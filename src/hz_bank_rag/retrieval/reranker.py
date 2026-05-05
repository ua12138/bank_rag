from __future__ import annotations

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError
from hz_bank_rag.core.types import RetrievalHit


class SiliconFlowReranker:
    """使用 SiliconFlow Rerank API 做最终重排。"""

    def __init__(self, model: str | None = None) -> None:
        self.client = SiliconFlowClient()
        self.model = model or settings.siliconflow_rerank_model

    def rerank(self, query: str, hits: list[RetrievalHit], top_k: int) -> list[RetrievalHit]:
        """对融合后的候选集做语义重排。

        先保留融合分作为兜底，再叠加 rerank 分，避免单一模型波动导致抖动。
        """

        if not hits:
            return []

        documents = [hit.text for hit in hits]

        try:
            rows = self.client.rerank(query=query, documents=documents, model=self.model, top_n=min(top_k, len(hits)))
        except SiliconFlowError:
            # Rerank 失败时回退融合分排序，保证问答链路可用。
            sorted_hits = sorted(hits, key=lambda item: item.score, reverse=True)
            for hit in sorted_hits[:top_k]:
                hit.rerank_score = hit.score
            return sorted_hits[:top_k]

        # 按返回 index 找回原始 hit，并组合新分数。
        reranked: list[RetrievalHit] = []
        for row in rows:
            idx = row["index"]
            rerank_score = float(row["score"])
            if idx < 0 or idx >= len(hits):
                continue
            hit = hits[idx]
            hit.rerank_score = rerank_score
            hit.score = hit.score + 0.35 * rerank_score
            reranked.append(hit)

        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k]
