from __future__ import annotations

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError


class QueryRewriter:
    """查询改写器：把口语化问题改写为更适合检索的查询。"""

    def __init__(self, model: str | None = None) -> None:
        self.client = SiliconFlowClient()
        self.model = model or settings.siliconflow_chat_model

    def rewrite(self, query: str) -> str:
        normalized = query.strip()
        if not normalized:
            return normalized

        system_prompt = (
            "你是银行运维知识库的查询改写器。"
            "请把用户问题改写为简洁、可检索、包含关键术语的中文检索查询。"
            "仅输出改写结果，不要解释。"
        )
        user_prompt = f"原始问题：{normalized}\n请输出改写后的检索查询："

        try:
            rewritten = self.client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                temperature=0.0,
                max_tokens=128,
            )
            return rewritten or normalized
        except SiliconFlowError:
            # 改写失败时直接回退原问题，避免阻断主流程。
            return normalized
