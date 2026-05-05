from __future__ import annotations

import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from hz_bank_rag.core.types import RetrievalHit
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.vector_store import BaseVectorStore


class HybridRetriever:
    """BM25 + Vector hybrid retrieval with RRF fusion."""

    def __init__(self, bm25_store: BM25Store, vector_store: BaseVectorStore) -> None:
        self.bm25_store = bm25_store
        self.vector_store = vector_store

    def search(
        self,
        kb_id: str,
        query: str,
        kb_chunk_map: dict[str, dict],
        top_k: int = 5,
        candidate_multiplier: int = 4,
    ) -> list[RetrievalHit]:
        candidate_k = max(top_k * candidate_multiplier, top_k)

        use_milvus_sparse = bool(
            hasattr(self.vector_store, "search_sparse") and getattr(self.vector_store, "sparse_available", False)
        )

        # Run sparse+dense retrieval in parallel to reduce end-to-end latency.
        with ThreadPoolExecutor(max_workers=2) as pool:
            if use_milvus_sparse:
                sparse_future = pool.submit(self.vector_store.search_sparse, query=query, kb_id=kb_id, top_k=candidate_k)
            else:
                sparse_future = pool.submit(self.bm25_store.search, kb_id=kb_id, query=query, top_k=candidate_k)
            dense_future = pool.submit(self.vector_store.search, query=query, kb_id=kb_id, top_k=candidate_k)
            sparse_hits = sparse_future.result()
            dense_hits = dense_future.result()

        sparse_norm = self._normalize_scores(sparse_hits)
        dense_norm = self._normalize_scores(dense_hits)

        rank_map: dict[str, dict[str, float]] = defaultdict(dict)
        for rank, (chunk_id, score) in enumerate(sparse_hits, start=1):
            rank_map[chunk_id]["bm25_rank"] = rank
            rank_map[chunk_id]["bm25_score"] = score
            rank_map[chunk_id]["bm25_norm"] = sparse_norm.get(chunk_id, 0.0)
        for rank, (chunk_id, score) in enumerate(dense_hits, start=1):
            rank_map[chunk_id]["vector_rank"] = rank
            rank_map[chunk_id]["vector_score"] = score
            rank_map[chunk_id]["vector_norm"] = dense_norm.get(chunk_id, 0.0)

        merged: list[RetrievalHit] = []
        for chunk_id, score_info in rank_map.items():
            chunk_row = kb_chunk_map.get(chunk_id)
            if chunk_row is None:
                continue

            # RRF gives robust rank-level fusion across heterogeneous retrievers.
            rrf_score = self._rrf(score_info.get("bm25_rank")) + self._rrf(score_info.get("vector_rank"))

            # Add small normalized-score signal to break ties among same rank patterns.
            final_score = rrf_score + 0.2 * score_info.get("bm25_norm", 0.0) + 0.2 * score_info.get("vector_norm", 0.0)

            merged.append(
                RetrievalHit(
                    chunk_id=chunk_id,
                    doc_id=chunk_row["doc_id"],
                    text=chunk_row["text"],
                    score=final_score,
                    source="hybrid",
                    bm25_score=score_info.get("bm25_score", 0.0),
                    vector_score=score_info.get("vector_score", 0.0),
                    rrf_score=rrf_score,
                    metadata=chunk_row.get("metadata", {}),
                )
            )

        merged.sort(key=lambda hit: hit.score, reverse=True)
        return merged[:candidate_k]

    @staticmethod
    def _rrf(rank: int | None, k: int = 60) -> float:
        if rank is None:
            return 0.0
        return 1.0 / (k + rank)

    @staticmethod
    def _normalize_scores(hits: list[tuple[str, float]]) -> dict[str, float]:
        if not hits:
            return {}
        values = [score for _, score in hits]
        high = max(values)
        low = min(values)
        if math.isclose(high, low):
            return {chunk_id: 1.0 for chunk_id, _ in hits}
        return {chunk_id: (score - low) / (high - low) for chunk_id, score in hits}
