from __future__ import annotations

from dataclasses import asdict, dataclass

from RAG_PLUS.config import plus_settings
from RAG_PLUS.redis_runtime import RedisRuntime


@dataclass
class RouteDecision:
    complexity_score: int
    level: str
    risky: bool
    reason: str
    selected_model: str
    use_rerank: bool

    def to_dict(self) -> dict:
        return asdict(self)


class SmartModelRouter:
    """
    智能路由器：
    - 简单问题 -> 小模型（低成本低时延）
    - 复杂问题 -> 大模型（高质量）
    - 高风险问题 -> 风险模型池（更保守）
    """

    def __init__(self, runtime: RedisRuntime) -> None:
        self.runtime = runtime

    def route(self, query: str) -> RouteDecision:
        text = (query or "").strip()
        length_score = min(len(text) // 12, 40)

        complex_tokens = [
            "对比",
            "根因",
            "排障",
            "多轮",
            "上下文",
            "流程",
            "架构",
            "优化",
            "为什么",
            "如何",
        ]
        complex_score = sum(5 for token in complex_tokens if token in text)
        multi_clause_bonus = 12 if text.count("，") + text.count("。") + text.count("?") + text.count("？") >= 3 else 0

        risky_tokens = ["删库", "重启生产", "故障切换", "紧急变更", "回滚", "资金", "合规", "审计"]
        risky = any(token in text for token in risky_tokens)

        score = min(100, length_score + complex_score + multi_clause_bonus + (25 if risky else 0))
        simple_t = plus_settings.route_simple_threshold
        complex_t = plus_settings.route_complex_threshold

        if risky:
            level = "risky"
            pool = plus_settings.parse_pool(plus_settings.risky_model_pool)
            reason = "命中高风险关键词，优先走风险模型池"
            use_rerank = True
        elif score <= simple_t:
            level = "simple"
            pool = plus_settings.parse_pool(plus_settings.small_model_pool)
            reason = "复杂度低，走小模型降低时延与成本"
            use_rerank = False
        elif score <= complex_t:
            level = "standard"
            pool = plus_settings.parse_pool(plus_settings.small_model_pool) + plus_settings.parse_pool(
                plus_settings.large_model_pool
            )[:1]
            reason = "中等复杂度，采用混合模型池"
            use_rerank = True
        else:
            level = "complex"
            pool = plus_settings.parse_pool(plus_settings.large_model_pool)
            reason = "复杂度高，走大模型保障质量"
            use_rerank = True

        selected_model = self.runtime.select_from_pool(name=f"model:{level}", pool=pool)
        return RouteDecision(
            complexity_score=score,
            level=level,
            risky=risky,
            reason=reason,
            selected_model=selected_model,
            use_rerank=use_rerank,
        )

