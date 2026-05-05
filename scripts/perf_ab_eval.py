from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from hz_bank_rag.core.config import settings
from hz_bank_rag.retrieval.hybrid_retriever import HybridRetriever
from hz_bank_rag.retrieval.query_rewrite import QueryRewriter
from hz_bank_rag.retrieval.reranker import SiliconFlowReranker
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.metadata_store import MetadataStore
from hz_bank_rag.storage.rag_repository import RAGRepository
from hz_bank_rag.storage.vector_store import InMemoryVectorStore, MilvusVectorStore


@dataclass
class QueryCase:
    query: str
    expected_keywords: list[str]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A/B evaluation for keyword layer + family dedup/freshness in medium concurrency RAG retrieval."
    )
    parser.add_argument("--kb-id", default=settings.default_kb_id)
    parser.add_argument("--queries-file", default="data/eval_samples/perf_queries.json")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=settings.search_top_k)
    parser.add_argument("--candidate-multiplier", type=int, default=settings.candidate_multiplier)
    parser.add_argument("--use-rewrite", action="store_true", default=False)
    parser.add_argument("--use-rerank", action="store_true", default=True)
    parser.add_argument("--freshness-weight", type=float, default=0.08)
    parser.add_argument("--min-filter-keep-ratio", type=float, default=0.15)
    parser.add_argument("--min-filter-keep-count", type=int, default=200)
    return parser.parse_args()


def _build_runtime() -> tuple[MetadataStore, RAGRepository, HybridRetriever, QueryRewriter, SiliconFlowReranker]:
    meta = MetadataStore(settings.sqlite_path)
    bm25 = BM25Store()
    vector_store = (
        MilvusVectorStore(
            uri=settings.milvus_uri,
            dim=settings.vector_dim,
            token=settings.milvus_token,
            collection_name=settings.milvus_collection,
            consistency_level=settings.milvus_consistency_level,
            enable_dynamic_field=settings.milvus_enable_dynamic_field,
        )
        if settings.use_milvus
        else InMemoryVectorStore(settings.vector_dim)
    )
    repo = RAGRepository(metadata=meta, vector_store=vector_store, bm25=bm25)
    retriever = HybridRetriever(bm25_store=bm25, vector_store=vector_store)
    rewriter = QueryRewriter()
    reranker = SiliconFlowReranker()
    return meta, repo, retriever, rewriter, reranker


def _load_cases(path: Path) -> list[QueryCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases: list[QueryCase] = []
    for row in raw:
        query = str(row.get("query", "")).strip()
        if not query:
            continue
        expected = [str(x).strip() for x in row.get("expected_keywords", []) if str(x).strip()]
        cases.append(QueryCase(query=query, expected_keywords=expected))
    if not cases:
        raise RuntimeError(f"empty query cases: {path}")
    return cases


def _to_timestamp(text: str) -> float:
    if not text:
        return 0.0
    value = text.strip().replace("T", " ")
    if len(value) == 19:
        formats = ["%Y-%m-%d %H:%M:%S"]
    else:
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _family_key(file_path: str) -> str:
    name = Path(file_path).stem.lower().strip()
    name = re.sub(r"[\s_\-]+", "-", name)
    name = re.sub(r"(v|ver|版本)[-_]?\d+(\.\d+)*", "", name)
    name = re.sub(r"\d{4}[-_/]?\d{2}[-_/]?\d{2}", "", name)
    name = re.sub(r"\d{8,14}", "", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name or Path(file_path).name.lower()


def _load_doc_meta_map(db_path: str, kb_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, str], float, float]:
    doc_map: dict[str, dict[str, Any]] = {}
    family_latest_doc: dict[str, str] = {}
    family_latest_ts: dict[str, float] = {}
    timestamps: list[float] = []

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT doc_id, file_path, created_at FROM documents WHERE kb_id = ?",
            (kb_id,),
        ).fetchall()
    finally:
        conn.close()

    for doc_id, file_path, created_at in rows:
        ts = _to_timestamp(created_at or "")
        family = _family_key(file_path or "")
        doc_map[doc_id] = {
            "file_path": file_path or "",
            "created_at": created_at or "",
            "ts": ts,
            "family": family,
        }
        timestamps.append(ts)
        if family not in family_latest_ts or ts > family_latest_ts[family]:
            family_latest_ts[family] = ts
            family_latest_doc[family] = doc_id

    if not timestamps:
        return doc_map, family_latest_doc, 0.0, 1.0
    return doc_map, family_latest_doc, min(timestamps), max(timestamps)


def _extract_keywords(query: str) -> list[str]:
    q = query.strip()
    if not q:
        return []

    strong_patterns = re.findall(r"[A-Z]{2,}[A-Z0-9_\-]{1,}|[A-Z]{1,}\d{2,}", q)
    chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,8}", q)
    en_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", q)

    merged: list[str] = []
    for token in strong_patterns + chinese_tokens + en_tokens:
        token = token.strip()
        if token and token not in merged:
            merged.append(token)
    return merged[:8]


def _keyword_filter(
    query: str,
    chunk_map: dict[str, dict[str, Any]],
    min_keep_ratio: float,
    min_keep_count: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    keywords = _extract_keywords(query)
    if not keywords:
        return chunk_map, {"enabled": False, "keywords": [], "kept": len(chunk_map), "reason": "no_keywords"}

    lowered = [kw.lower() for kw in keywords]
    kept: dict[str, dict[str, Any]] = {}
    for chunk_id, row in chunk_map.items():
        metadata = row.get("metadata", {}) or {}
        text = row.get("text", "")
        searchable = " ".join(
            [
                str(text),
                str(metadata.get("file_name", "")),
                str(metadata.get("file_path", "")),
                str(metadata.get("doc_title", "")),
            ]
        ).lower()
        if any(kw in searchable for kw in lowered):
            kept[chunk_id] = row

    total = len(chunk_map)
    kept_count = len(kept)
    safe_floor = max(min_keep_count, int(total * min_keep_ratio))
    if kept_count < safe_floor:
        return chunk_map, {
            "enabled": False,
            "keywords": keywords,
            "kept": total,
            "reason": f"kept_too_few({kept_count}<{safe_floor})",
        }

    return kept, {"enabled": True, "keywords": keywords, "kept": kept_count, "reason": "ok"}


def _dedup_and_freshness(
    hits: list[Any],
    doc_meta: dict[str, dict[str, Any]],
    ts_min: float,
    ts_max: float,
    top_k: int,
    freshness_weight: float,
) -> list[Any]:
    if not hits:
        return []

    span = max(1.0, ts_max - ts_min)
    family_best: dict[str, Any] = {}
    for hit in hits:
        info = doc_meta.get(hit.doc_id, {})
        family = info.get("family", hit.doc_id)
        ts = float(info.get("ts", 0.0))
        freshness = (ts - ts_min) / span
        adjusted = hit.score + freshness_weight * freshness

        current = family_best.get(family)
        if current is None or adjusted > current[0]:
            family_best[family] = (adjusted, hit)

    merged = [item[1] for item in family_best.values()]
    merged.sort(key=lambda x: x.score, reverse=True)
    return merged[:top_k]


def _quality_metrics(
    hits: list[Any],
    top_k: int,
    expected_keywords: list[str],
    doc_meta: dict[str, dict[str, Any]],
    family_latest_doc: dict[str, str],
) -> dict[str, float]:
    top_hits = hits[:top_k]
    if not top_hits:
        return {
            "duplicate_rate": 0.0,
            "latest_hit_rate": 0.0,
            "precision_at_k_proxy": 0.0,
        }

    families = []
    latest_hits = 0
    proxy_relevant = 0
    expected = [x.lower() for x in expected_keywords]

    for hit in top_hits:
        info = doc_meta.get(hit.doc_id, {})
        family = info.get("family", hit.doc_id)
        families.append(family)

        latest_doc = family_latest_doc.get(family)
        if latest_doc and latest_doc == hit.doc_id:
            latest_hits += 1

        if expected:
            joined = f"{hit.text} {json.dumps(hit.metadata or {}, ensure_ascii=False)}".lower()
            if any(token in joined for token in expected):
                proxy_relevant += 1

    duplicate = len(top_hits) - len(set(families))
    precision_proxy = (proxy_relevant / len(top_hits)) if expected else 0.0
    return {
        "duplicate_rate": duplicate / len(top_hits),
        "latest_hit_rate": latest_hits / len(top_hits),
        "precision_at_k_proxy": precision_proxy,
    }


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def _run_mode(
    mode: str,
    cases: list[QueryCase],
    rounds: int,
    concurrency: int,
    kb_id: str,
    chunk_map: dict[str, dict[str, Any]],
    retriever: HybridRetriever,
    rewriter: QueryRewriter,
    reranker: SiliconFlowReranker,
    use_rewrite: bool,
    use_rerank: bool,
    top_k: int,
    candidate_multiplier: int,
    doc_meta: dict[str, dict[str, Any]],
    family_latest_doc: dict[str, str],
    ts_min: float,
    ts_max: float,
    freshness_weight: float,
    min_filter_keep_ratio: float,
    min_filter_keep_count: int,
) -> dict[str, Any]:
    workload = cases * max(1, rounds)
    latencies: list[float] = []
    duplicate_rates: list[float] = []
    latest_rates: list[float] = []
    precision_proxy: list[float] = []
    keyword_kept: list[int] = []
    keyword_enabled_count = 0
    rerank_fallback_count = 0

    def _one(case: QueryCase) -> dict[str, Any]:
        start = time.perf_counter()
        query = case.query
        rewritten = query
        if use_rewrite:
            rewritten = rewriter.rewrite(query)

        active_map = chunk_map
        keyword_meta = {"enabled": False, "keywords": [], "kept": len(chunk_map), "reason": "mode_a"}
        if mode == "B":
            active_map, keyword_meta = _keyword_filter(
                query=rewritten,
                chunk_map=chunk_map,
                min_keep_ratio=min_filter_keep_ratio,
                min_keep_count=min_filter_keep_count,
            )

        candidate_k = max(top_k * candidate_multiplier, top_k)
        hits = retriever.search(
            kb_id=kb_id,
            query=rewritten,
            kb_chunk_map=active_map,
            top_k=top_k,
            candidate_multiplier=candidate_multiplier,
        )
        hits = hits[:candidate_k]

        if use_rerank:
            try:
                hits = reranker.rerank(rewritten, hits, top_k=top_k)
            except Exception:
                hits = hits[:top_k]
                fallback = 1
            else:
                fallback = 0
        else:
            hits = hits[:top_k]
            fallback = 0

        if mode == "B":
            hits = _dedup_and_freshness(
                hits=hits,
                doc_meta=doc_meta,
                ts_min=ts_min,
                ts_max=ts_max,
                top_k=top_k,
                freshness_weight=freshness_weight,
            )

        metrics = _quality_metrics(
            hits=hits,
            top_k=top_k,
            expected_keywords=case.expected_keywords,
            doc_meta=doc_meta,
            family_latest_doc=family_latest_doc,
        )
        cost_ms = (time.perf_counter() - start) * 1000
        return {
            "latency_ms": cost_ms,
            "duplicate_rate": metrics["duplicate_rate"],
            "latest_hit_rate": metrics["latest_hit_rate"],
            "precision_at_k_proxy": metrics["precision_at_k_proxy"],
            "keyword_meta": keyword_meta,
            "rerank_fallback": fallback,
        }

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(_one, case) for case in workload]
        for future in as_completed(futures):
            row = future.result()
            latencies.append(row["latency_ms"])
            duplicate_rates.append(row["duplicate_rate"])
            latest_rates.append(row["latest_hit_rate"])
            precision_proxy.append(row["precision_at_k_proxy"])
            rerank_fallback_count += int(row["rerank_fallback"])
            km = row["keyword_meta"]
            keyword_kept.append(int(km.get("kept", 0)))
            if km.get("enabled", False):
                keyword_enabled_count += 1
    wall_cost = max(0.0001, time.perf_counter() - wall_start)

    return {
        "mode": mode,
        "requests": len(workload),
        "concurrency": concurrency,
        "qps": len(workload) / wall_cost,
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "p99": _percentile(latencies, 0.99),
            "avg": statistics.fmean(latencies) if latencies else 0.0,
        },
        "quality": {
            "duplicate_rate_avg": statistics.fmean(duplicate_rates) if duplicate_rates else 0.0,
            "latest_hit_rate_avg": statistics.fmean(latest_rates) if latest_rates else 0.0,
            "precision_at_k_proxy_avg": statistics.fmean(precision_proxy) if precision_proxy else 0.0,
        },
        "feature_stats": {
            "keyword_layer_enabled_ratio": (keyword_enabled_count / len(workload)) if workload else 0.0,
            "keyword_keep_avg": statistics.fmean(keyword_kept) if keyword_kept else 0.0,
            "rerank_fallback_count": rerank_fallback_count,
        },
    }


def _compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    def _delta(field: str) -> float:
        av = float(a["latency_ms"][field])
        bv = float(b["latency_ms"][field])
        if av == 0:
            return 0.0
        return (bv - av) / av

    def _quality_delta(field: str) -> float:
        av = float(a["quality"][field])
        bv = float(b["quality"][field])
        if av == 0:
            return 0.0
        return (bv - av) / av

    return {
        "latency_delta_ratio": {
            "p50": _delta("p50"),
            "p95": _delta("p95"),
            "p99": _delta("p99"),
            "avg": _delta("avg"),
        },
        "qps_delta_ratio": ((b["qps"] - a["qps"]) / a["qps"]) if a["qps"] else 0.0,
        "quality_delta_ratio": {
            "duplicate_rate_avg": _quality_delta("duplicate_rate_avg"),
            "latest_hit_rate_avg": _quality_delta("latest_hit_rate_avg"),
            "precision_at_k_proxy_avg": _quality_delta("precision_at_k_proxy_avg"),
        },
    }


def _write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"perf_ab_report_{stamp}.json"
    md_path = out_dir / f"perf_ab_report_{stamp}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8-sig")

    a = report["result"]["A"]
    b = report["result"]["B"]
    c = report["result"]["compare"]
    lines = [
        "# 性能 A/B 评估报告",
        "",
        f"- 时间: {report['timestamp']}",
        f"- KB: {report['kb_id']}",
        f"- 并发: {report['config']['concurrency']}",
        f"- 轮次: {report['config']['rounds']}",
        f"- 请求总数/组: {a['requests']}",
        "",
        "## A 组（基线）",
        f"- P95(ms): {a['latency_ms']['p95']:.2f}",
        f"- QPS: {a['qps']:.2f}",
        f"- 重复证据率: {a['quality']['duplicate_rate_avg']:.4f}",
        f"- 最新命中率: {a['quality']['latest_hit_rate_avg']:.4f}",
        "",
        "## B 组（优化）",
        f"- P95(ms): {b['latency_ms']['p95']:.2f}",
        f"- QPS: {b['qps']:.2f}",
        f"- 重复证据率: {b['quality']['duplicate_rate_avg']:.4f}",
        f"- 最新命中率: {b['quality']['latest_hit_rate_avg']:.4f}",
        "",
        "## 对比（B 相比 A）",
        f"- P95 变化: {c['latency_delta_ratio']['p95'] * 100:.2f}%",
        f"- QPS 变化: {c['qps_delta_ratio'] * 100:.2f}%",
        f"- 重复证据率变化: {c['quality_delta_ratio']['duplicate_rate_avg'] * 100:.2f}%",
        f"- 最新命中率变化: {c['quality_delta_ratio']['latest_hit_rate_avg'] * 100:.2f}%",
        "",
        "## 判定建议",
        "- 若 B 组 P95 上升 <= 5%，且最新命中率提升 >= 15%，可灰度上线。",
        "- 若 B 组 P95 上升 > 10%，建议仅在强关键词命中时启用关键词层。",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return json_path, md_path


def main() -> int:
    args = _parse_args()
    queries_path = Path(args.queries_file)
    if not queries_path.exists():
        raise FileNotFoundError(f"queries file not found: {queries_path}")

    cases = _load_cases(queries_path)
    meta, repo, retriever, rewriter, reranker = _build_runtime()
    chunk_map = repo.get_kb_chunk_map(args.kb_id)
    if not chunk_map:
        raise RuntimeError(f"kb is empty: {args.kb_id}, please ingest data first")

    doc_meta, family_latest_doc, ts_min, ts_max = _load_doc_meta_map(settings.sqlite_path, args.kb_id)
    if not doc_meta:
        raise RuntimeError(f"no documents found in kb: {args.kb_id}")

    result_a = _run_mode(
        mode="A",
        cases=cases,
        rounds=args.rounds,
        concurrency=args.concurrency,
        kb_id=args.kb_id,
        chunk_map=chunk_map,
        retriever=retriever,
        rewriter=rewriter,
        reranker=reranker,
        use_rewrite=args.use_rewrite,
        use_rerank=args.use_rerank,
        top_k=args.top_k,
        candidate_multiplier=args.candidate_multiplier,
        doc_meta=doc_meta,
        family_latest_doc=family_latest_doc,
        ts_min=ts_min,
        ts_max=ts_max,
        freshness_weight=args.freshness_weight,
        min_filter_keep_ratio=args.min_filter_keep_ratio,
        min_filter_keep_count=args.min_filter_keep_count,
    )
    result_b = _run_mode(
        mode="B",
        cases=cases,
        rounds=args.rounds,
        concurrency=args.concurrency,
        kb_id=args.kb_id,
        chunk_map=chunk_map,
        retriever=retriever,
        rewriter=rewriter,
        reranker=reranker,
        use_rewrite=args.use_rewrite,
        use_rerank=args.use_rerank,
        top_k=args.top_k,
        candidate_multiplier=args.candidate_multiplier,
        doc_meta=doc_meta,
        family_latest_doc=family_latest_doc,
        ts_min=ts_min,
        ts_max=ts_max,
        freshness_weight=args.freshness_weight,
        min_filter_keep_ratio=args.min_filter_keep_ratio,
        min_filter_keep_count=args.min_filter_keep_count,
    )
    compare = _compare(result_a, result_b)

    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "kb_id": args.kb_id,
        "config": {
            "queries_file": str(queries_path),
            "concurrency": args.concurrency,
            "rounds": args.rounds,
            "top_k": args.top_k,
            "candidate_multiplier": args.candidate_multiplier,
            "use_rewrite": bool(args.use_rewrite),
            "use_rerank": bool(args.use_rerank),
            "freshness_weight": args.freshness_weight,
            "min_filter_keep_ratio": args.min_filter_keep_ratio,
            "min_filter_keep_count": args.min_filter_keep_count,
        },
        "result": {
            "A": result_a,
            "B": result_b,
            "compare": compare,
        },
    }
    json_path, md_path = _write_report(report, Path(args.out_dir))
    print(f"A/B report JSON: {json_path}")
    print(f"A/B report MD  : {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
