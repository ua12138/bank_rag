from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    file_path: str = Field(..., description="Document path")
    parser_type: str = Field(default="auto", description="Parser type")
    chunk_strategy: str = Field(default="recursive", description="Chunk strategy: recursive|semantic")


class BulkIngestRequest(BaseModel):
    file_paths: list[str] = Field(..., description="Document path list")
    chunk_strategy: str = Field(default="recursive", description="Chunk strategy")


class QueryRequest(BaseModel):
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
    dataset: list[dict]


class RagasBuildSample(BaseModel):
    question: str
    ground_truth: str


class RagasBuildRequest(BaseModel):
    kb_id: str
    samples: list[RagasBuildSample]
    top_k: int = 5
    candidate_multiplier: int = 4
    fast_mode: bool = True


class BadCaseListRequest(BaseModel):
    kb_id: str | None = None
    limit: int = 50
