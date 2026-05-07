from __future__ import annotations

"""全局配置模块：集中管理 RAG 服务的运行参数。"""

from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class MilvusFields:
    """Milvus 字段名约定，避免各处硬编码字符串。"""
    primary_key: str = "chunk_id"
    vector: str = "vector"
    sparse_vector: str = "sparse_vector"
    kb_id: str = "kb_id"
    doc_id: str = "doc_id"
    text: str = "text"
    bm25_function: str = "bm25_function"


class Settings(BaseSettings):
    """应用配置对象。

    说明:
    - 通过 `HZ_RAG_` 前缀环境变量覆盖默认值。
    - 这里是项目大多数行为的“总开关”。
    """
    app_name: str = "hz-bank-rag"
    sqlite_path: str = "./rag_meta.db"
    data_dir: str = "./data"
    default_kb_id: str = "hz-bank-demo"

    use_milvus: bool = True
    milvus_uri: str = "http://47.111.101.201:19530"
    milvus_token: str | None = None
    milvus_collection: str = "hz_bank_rag_chunks"
    milvus_consistency_level: str = "Strong"
    milvus_enable_dynamic_field: bool = True

    vector_dim: int = 1024
    search_top_k: int = 5
    candidate_multiplier: int = 4
    chunk_strategy: str = "recursive"
    chunk_size: int = 450
    chunk_overlap: int = 80

    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_api_key: str = "sk-ntgwbovfhoegynefsssoqtvuseyliywfdllvjjvlsuezfeik"
    siliconflow_timeout_seconds: float = 60.0
    siliconflow_embedding_batch_size: int = 32

    siliconflow_embedding_model: str = "BAAI/bge-large-zh-v1.5"
    siliconflow_rerank_model: str = "BAAI/bge-reranker-v2-m3"
    siliconflow_chat_model: str = "Qwen/Qwen2.5-7B-Instruct"
    siliconflow_vision_model: str = "Qwen/Qwen2.5-VL-7B-Instruct"

    enable_clip: bool = True
    clip_model_name: str = "openai/clip-vit-base-patch32"

    siliconflow_chat_temperature: float = 0.2
    siliconflow_chat_max_tokens: int = 1024

    enable_query_cache: bool = True
    query_cache_ttl_seconds: int = 300
    query_cache_max_size: int = 500

    # L1: Embedding 缓存（文本→向量，永不失效）
    enable_embedding_cache: bool = True
    embedding_cache_max_size: int = 10000

    # L2: 检索结果语义缓存
    enable_retrieval_cache: bool = True
    retrieval_cache_ttl_seconds: int = 180
    retrieval_cache_max_size: int = 200
    retrieval_cache_similarity_threshold: float = 0.92

    # L3: 答案缓存语义匹配阈值
    answer_cache_semantic_threshold: float = 0.95

    conversation_max_turns: int = 8
    conversation_max_chars: int = 3000
    conversation_summary_max_chars: int = 800

    enable_keyword_layer: bool = True
    keyword_layer_min_keep_ratio: float = 0.15
    keyword_layer_min_keep_count: int = 200
    keyword_strong_pattern_enabled: bool = True
    keyword_model_enabled: bool = False
    keyword_model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    keyword_model_max_terms: int = 8

    near_duplicate_hamming_threshold: int = 3
    near_duplicate_reject: bool = False
    default_retrieval_scope: str = "active_only"
    default_freshness_weight: float = 0.08
    default_dedup_by_family: bool = True

    model_config = SettingsConfigDict(env_prefix="HZ_RAG_", extra="ignore")


settings = Settings()
milvus_fields = MilvusFields()
