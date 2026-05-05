from __future__ import annotations

import jieba
from rank_bm25 import BM25Okapi


class BM25Store:
    """按知识库维度维护 BM25 索引。"""

    def __init__(self) -> None:
        self._indexes: dict[str, BM25Okapi | None] = {}
        self._chunk_ids: dict[str, list[str]] = {}
        self._texts: dict[str, list[str]] = {}

    def rebuild(self, kb_id: str, chunk_map: dict[str, str]) -> None:
        chunk_ids = list(chunk_map.keys())
        self._chunk_ids[kb_id] = chunk_ids
        self._texts[kb_id] = [chunk_map[cid] for cid in chunk_ids]
        tokenized = [list(jieba.cut(text)) for text in self._texts[kb_id]]
        self._indexes[kb_id] = BM25Okapi(tokenized) if tokenized else None

    def clear(self, kb_id: str) -> None:
        self._indexes.pop(kb_id, None)
        self._chunk_ids.pop(kb_id, None)
        self._texts.pop(kb_id, None)

    def search(self, kb_id: str, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        index = self._indexes.get(kb_id)
        if index is None:
            return []
        scores = index.get_scores(list(jieba.cut(query)))
        order = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:top_k]
        chunk_ids = self._chunk_ids.get(kb_id, [])
        return [(chunk_ids[idx], float(scores[idx])) for idx in order]
