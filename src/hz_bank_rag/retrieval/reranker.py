from __future__ import annotations

"""重排模块：对混合检索结果做语义重排。"""

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError
from hz_bank_rag.core.types import RetrievalHit


class SiliconFlowReranker:
    """使用 SiliconFlow Rerank API 做最终重排。"""

    def __init__(self, model: str | None = None) -> None:
        self.client = SiliconFlowClient()
        self.model = model or settings.siliconflow_rerank_model

    def rerank(self, query: str, hits: list[RetrievalHit], top_k: int) -> list[RetrievalHit]:
        """对候选集合执行重排。

        失败场景: API 异常时回退到原融合分排序。
        """
        if not hits:
            return []

        documents = [hit.text for hit in hits]
        try:
            rows = self.client.rerank(query=query, documents=documents, model=self.model, top_n=min(top_k, len(hits)))
        except SiliconFlowError:
            # 重排失败时保持可用性：直接使用融合排序结果。
            sorted_hits = sorted(hits, key=lambda item: item.score, reverse=True)
            for hit in sorted_hits[:top_k]:
                hit.rerank_score = hit.score
            return sorted_hits[:top_k]

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
