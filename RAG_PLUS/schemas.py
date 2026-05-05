from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scopes: list[str]


class PlusQueryRequest(BaseModel):
    kb_id: str
    query: str
    session_id: str = ""
    use_memory: bool = True
    top_k: int = Field(default=5, ge=1, le=30)
    candidate_multiplier: int = Field(default=4, ge=1, le=10)
    refresh_cache: bool = False


class ToolRegistrationRequest(BaseModel):
    tool_id: str
    name: str
    description: str
    endpoint: str
    method: str = "POST"
    tags: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=lambda: ["tools:read"])
    owner: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    avg_latency_ms: int = Field(default=100, ge=1, le=100000)


class ToolSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=8, ge=1, le=50)
    required_tags: list[str] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    kb_id: str
    query: str
    session_id: str = ""
    top_k: int = Field(default=5, ge=1, le=30)
    candidate_multiplier: int = Field(default=4, ge=1, le=10)

