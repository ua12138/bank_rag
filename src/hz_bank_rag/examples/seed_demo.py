from __future__ import annotations

"""示例数据灌库脚本：把 demo 文档批量导入知识库。"""

from pathlib import Path

from hz_bank_rag.core.config import settings
from hz_bank_rag.ingestion.document_parser import IMAGE_SUFFIXES, PDF_SUFFIXES, PPT_SUFFIXES, TEXT_SUFFIXES, WORD_SUFFIXES
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.metadata_store import MetadataStore
from hz_bank_rag.storage.rag_repository import RAGRepository
from hz_bank_rag.storage.vector_store import InMemoryVectorStore, MilvusVectorStore


SUPPORTED_SUFFIXES = set(TEXT_SUFFIXES) | set(PDF_SUFFIXES) | set(WORD_SUFFIXES) | set(PPT_SUFFIXES) | set(IMAGE_SUFFIXES)

# 评估数据不参与 demo 灌库，避免污染检索样本。
EXCLUDED_FILE_NAMES = {
    "ragas_dataset_samples.json",
    "ragas_eval.json",
    "bad_case_payload_samples.json",
}
EXCLUDED_DIR_NAMES = {"eval_samples", "evaluation", "fixtures"}


def build_repository() -> RAGRepository:
    """构建一个可直接入库的仓储实例。"""
    metadata = MetadataStore(settings.sqlite_path)
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
    return RAGRepository(metadata=metadata, vector_store=vector_store, bm25=bm25)


def _resolve_demo_dir(data_dir: Path) -> Path:
    """兼容两种目录形态：`data/` 或 `data/demo_kb/`。"""
    direct = data_dir
    nested = data_dir / "demo_kb"
    if direct.exists() and any(child.is_file() for child in direct.iterdir()):
        return direct
    if nested.exists() and any(child.is_file() for child in nested.iterdir()):
        return nested
    return direct


def _collect_demo_files(resolved_dir: Path) -> tuple[list[str], list[str]]:
    """扫描可入库文件，并返回 `(可入库列表, 跳过列表)`。"""
    file_paths: list[str] = []
    skipped: list[str] = []

    for path in sorted(resolved_dir.rglob("*"), key=lambda p: str(p).lower()):
        if not path.is_file():
            continue
        if any(part.lower() in EXCLUDED_DIR_NAMES for part in path.parts):
            skipped.append(str(path.relative_to(resolved_dir)))
            continue
        if path.name in EXCLUDED_FILE_NAMES:
            skipped.append(str(path.relative_to(resolved_dir)))
            continue

        suffix = path.suffix.lower()
        if suffix in SUPPORTED_SUFFIXES:
            file_paths.append(str(path.resolve()))
        else:
            skipped.append(str(path.relative_to(resolved_dir)))

    return file_paths, skipped


def seed_demo_data(repo: RAGRepository, kb_id: str, data_dir: Path) -> dict:
    """执行 demo 灌库。

    返回:
    - 入库数量、入库文件、跳过文件及排除规则，方便排查。
    """
    resolved_dir = _resolve_demo_dir(data_dir)
    if not resolved_dir.exists():
        return {
            "kb_id": kb_id,
            "documents": [],
            "count": 0,
            "resolved_data_dir": str(resolved_dir.resolve()),
            "supported_suffixes": sorted(SUPPORTED_SUFFIXES),
            "excluded_file_names": sorted(EXCLUDED_FILE_NAMES),
            "excluded_dir_names": sorted(EXCLUDED_DIR_NAMES),
            "hint": "Data directory does not exist.",
        }

    file_paths, skipped = _collect_demo_files(resolved_dir)
    if not file_paths:
        return {
            "kb_id": kb_id,
            "documents": [],
            "count": 0,
            "resolved_data_dir": str(resolved_dir.resolve()),
            "supported_suffixes": sorted(SUPPORTED_SUFFIXES),
            "excluded_file_names": sorted(EXCLUDED_FILE_NAMES),
            "excluded_dir_names": sorted(EXCLUDED_DIR_NAMES),
            "skipped_files": skipped,
            "hint": "No supported files found to ingest.",
        }

    result = repo.bulk_ingest(kb_id=kb_id, file_paths=file_paths, chunk_strategy=settings.chunk_strategy)
    result["resolved_data_dir"] = str(resolved_dir.resolve())
    result["ingested_files"] = [Path(p).name for p in file_paths]
    result["skipped_files"] = skipped
    result["excluded_file_names"] = sorted(EXCLUDED_FILE_NAMES)
    result["excluded_dir_names"] = sorted(EXCLUDED_DIR_NAMES)
    return result


def main() -> None:
    """本地命令行入口。"""
    repo = build_repository()
    result = seed_demo_data(repo=repo, kb_id=settings.default_kb_id, data_dir=Path(settings.data_dir))
    print(result)


if __name__ == "__main__":
    main()
