from __future__ import annotations

"""API 请求模型定义：约束每个接口的输入参数。"""

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """单文档入库请求。"""

    file_path: str = Field(..., description="文档路径")
    parser_type: str = Field(default="auto", description="解析器类型")
    chunk_strategy: str = Field(default="recursive", description="切分策略: recursive|semantic")


class BulkIngestRequest(BaseModel):
    """批量入库请求。"""

    file_paths: list[str] = Field(..., description="文档路径列表")
    chunk_strategy: str = Field(default="recursive", description="切分策略")


class QueryRequest(BaseModel):
    """问答请求。"""

    kb_id: str
    query: str
    top_k: int = 5
    candidate_multiplier: int = 4
    fast_mode: bool = True
    session_id: str = ""
    use_memory: bool = True
    refresh_cache: bool = False
    retrieval_scope: str = "active_only"
    freshness_weight: float = 0.08
    dedup_by_family: bool = True


class BadCaseRequest(BaseModel):
    """bad case 记录请求。"""

    kb_id: str
    query: str
    rewritten_query: str = ""
    feedback: str
    retrieval_snapshot: dict = Field(default_factory=dict)
    auto_capture_snapshot: bool = True
    top_k: int = 5
    candidate_multiplier: int = 4
    fast_mode: bool = True
    category: str = "retrieval"
    severity: str = "medium"
    status: str = "open"
    expected_answer: str = ""
    retrieval_scope: str = "active_only"
    freshness_weight: float = 0.08
    dedup_by_family: bool = True


class BadCaseSnapshotRequest(BaseModel):
    """构建检索快照请求。"""

    kb_id: str
    query: str
    rewritten_query: str = ""
    top_k: int = 5
    candidate_multiplier: int = 4
    fast_mode: bool = True
    retrieval_scope: str = "active_only"
    freshness_weight: float = 0.08
    dedup_by_family: bool = True


class EvalRequest(BaseModel):
    """RAGAS 评估请求。"""

    dataset: list[dict]


class RagasBuildSample(BaseModel):
    """构建评估数据集时的单条样本。"""

    question: str
    ground_truth: str


class RagasBuildRequest(BaseModel):
    """在线构建 RAGAS 数据集请求。"""

    kb_id: str
    samples: list[RagasBuildSample]
    top_k: int = 5
    candidate_multiplier: int = 4
    fast_mode: bool = True


class BadCaseListRequest(BaseModel):
    """bad case 列表查询请求（保留模型）。"""

    kb_id: str | None = None
    limit: int = 50
