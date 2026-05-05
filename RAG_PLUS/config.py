from __future__ import annotations

"""RAG_PLUS 配置模块。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PlusSettings(BaseSettings):
    """RAG_PLUS 配置。

    通过 `HZ_RAG_PLUS_` 前缀环境变量覆盖默认值。
    """

    # 服务基础配置
    app_name: str = "hz-bank-rag-plus"
    api_prefix: str = "/plus"

    # 鉴权配置
    auth_secret: str = "change-me-rag-plus-secret"
    auth_token_ttl_seconds: int = 7200
    admin_username: str = "admin"
    admin_password: str = "admin123"

    # Redis 配置（不可用时会自动降级到本地内存）
    redis_enabled: bool = True
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_prefix: str = "hz_rag_plus"
    redis_cache_ttl_seconds: int = 180

    # 并发与限流
    max_inflight_global: int = 150
    max_inflight_per_kb: int = 60
    rate_limit_per_user_per_minute: int = 120
    inflight_slot_ttl_seconds: int = 20

    # 模型池配置
    small_model_pool: str = "Qwen/Qwen2.5-7B-Instruct"
    large_model_pool: str = "Qwen/Qwen2.5-14B-Instruct,Qwen/Qwen2.5-32B-Instruct"
    risky_model_pool: str = "Qwen/Qwen2.5-32B-Instruct"

    # 路由阈值
    route_simple_threshold: int = 25
    route_complex_threshold: int = 60

    # 检索默认参数
    default_top_k: int = 5
    default_candidate_multiplier: int = 4

    model_config = SettingsConfigDict(env_prefix="HZ_RAG_PLUS_", extra="ignore")

    def parse_pool(self, value: str) -> list[str]:
        """把逗号分隔模型池字符串转为列表。"""
        return [item.strip() for item in value.split(",") if item.strip()]


plus_settings = PlusSettings()
