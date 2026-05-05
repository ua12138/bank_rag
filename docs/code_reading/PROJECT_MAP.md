# PROJECT_MAP（函数级证据版）

## 1. 项目用途（以函数证据落地）

| 结论 | 证据文件 | 类/函数 | 谁调用它 | 它调用谁 | 核心入参 | 核心出参 |
|---|---|---|---|---|---|---|
| 提供 RAG HTTP 主服务（入库、问答、评估、bad-case） | `src/hz_bank_rag/api/main.py` | `build_app() -> app = build_app()` | `uvicorn hz_bank_rag.api.main:app` 导入模块时触发 | `MetadataStore(...)`, `BM25Store()`, `MilvusVectorStore(...)`, `RAGRepository(...)`, `HybridRetriever(...)`, `QAService(...)`, `RagasRunner()` | 无显式入参（读取 `settings`） | `FastAPI` 实例，包含 `/query`、`/knowledge-bases/*`、`/evaluate/*` 等路由 |
| 统一问答编排（缓存、检索、重排、生成、记忆） | `src/hz_bank_rag/service/qa_service.py` | `QAService.ask(...)` | `api/main.py::query`，`mcp/main.py::_call_tool(name='rag.query')` | `_make_cache_key`, `QueryCache.get`, `repo.get_kb_chunk_map`, `_retrieve_hits`, `_build_memory_context`, `_generate_answer`, `_save_conversation_turn`, `QueryCache.set` | `kb_id/query/top_k/candidate_multiplier/fast_mode/session_id/use_memory/refresh_cache` | `dict`：`answer/citations/rewritten_query/cache_hit/latency_ms/memory` |
| 混合召回（稀疏+稠密并行 + RRF） | `src/hz_bank_rag/retrieval/hybrid_retriever.py` | `HybridRetriever.search(...)` | `QAService._retrieve_hits`, `RAG_PLUS/rag_runtime.py::AdaptiveQAExecutor.ask` | `vector_store.search_sparse` 或 `bm25_store.search`; `vector_store.search`; `_normalize_scores`; `_rrf` | `kb_id/query/kb_chunk_map/top_k/candidate_multiplier` | `list[RetrievalHit]`（含 `bm25_score/vector_score/rrf_score`） |
| 语义重排（rerank） | `src/hz_bank_rag/retrieval/reranker.py` | `SiliconFlowReranker.rerank(...)` | `QAService._retrieve_hits`（`fast_mode=False`），`AdaptiveQAExecutor.ask`（`route.use_rerank=True`） | `SiliconFlowClient.rerank`；失败时回退本地分数排序 | `query`, `hits: list[RetrievalHit]`, `top_k` | 重排后的 `list[RetrievalHit]`（更新 `rerank_score` 与 `score`） |
| 查询改写（Rewrite） | `src/hz_bank_rag/retrieval/query_rewrite.py` | `QueryRewriter.rewrite(query)` | `QAService.ask/ask_stream/build_retrieval_snapshot`, `AdaptiveQAExecutor.ask` | `SiliconFlowClient.chat`；异常时返回原 query | `query: str` | `rewritten_query: str` |
| 文档入库主流程 | `src/hz_bank_rag/storage/rag_repository.py` | `RAGRepository.ingest_document(...)` | `api/main.py::ingest_document`, `bulk_ingest`, `examples/seed_demo.py::seed_demo_data` | `metadata.get_document_by_kb_and_path/hash`, `metadata.add_document`, `parse_document`, `clean_text`, `chunker.split`, `metadata.add_chunk`, `vector_store.upsert`, `_rebuild_bm25` | `kb_id/file_path/parser_type/chunk_strategy` | `dict`：`doc_id/file_hash/file_size/chunks/chunk_strategy` |
| 元数据读写与会话/BadCase 存储 | `src/hz_bank_rag/storage/metadata_store.py` | `MetadataStore` 关键函数：`get_kb_chunks/add_chunk/list_documents/add_bad_case/get_conversation_messages/...` | `RAGRepository`, `QAService`, `api/main.py` 路由 | SQLite `SELECT/INSERT/DELETE` | 视函数而定（例如 `kb_id/doc_id/session_id`） | `list[dict]/dict/None/int`（视函数） |
| 向量检索与稀疏 BM25（Milvus） | `src/hz_bank_rag/storage/vector_store.py` | `MilvusVectorStore.search`, `search_sparse` | `HybridRetriever.search` | `self.embedder.encode`, `self.client.search`（Milvus） | `query/kb_id/top_k` | `list[tuple[chunk_id, score]]` |
| RAGAS A/B 评估 | `src/hz_bank_rag/evaluation/ragas_runner.py` | `RagasRunner.evaluate_ab(dataset)` | `api/main.py::evaluate_ragas_ab`, `mcp/main.py::_call_tool(name='rag.evaluate_ragas_ab')` | `evaluate_lightweight`, `evaluate_official`, 聚合 delta | `dataset: list[dict]` | `dict`：`lightweight/official/delta_official_minus_lightweight` |
| MCP 封装（HTTP + JSON-RPC） | `src/hz_bank_rag/mcp/main.py` | `build_mcp_app()`, `_call_tool(...)`, `mcp_rpc(...)` | `uvicorn hz_bank_rag.mcp.main:app`；外部 Agent 请求 `/mcp` 或 `/tools/call` | `build_runtime`, `_tool_specs`, `runtime.qa.ask`, `runtime.repo.list_documents`, `runtime.ragas.evaluate_ab` | `JsonRpcRequest` 或 `ToolCallRequest` | `dict`（JSON-RPC result/error 或工具执行结果） |

## 2. 技术栈（绑定到实现函数）

| 技术 | 代码落点 | 证据函数/类 | 输入 | 输出/作用 |
|---|---|---|---|---|
| FastAPI | `src/hz_bank_rag/api/main.py`, `src/hz_bank_rag/mcp/main.py`, `RAG_PLUS/main.py` | `build_app()`, `build_mcp_app()` | 路由函数定义 | HTTP 服务对象 |
| Pydantic | `src/hz_bank_rag/api/schemas.py`, `src/hz_bank_rag/mcp/main.py` | `QueryRequest`, `JsonRpcRequest`, `ToolCallRequest` | 请求 JSON | 类型化请求对象 |
| SQLite | `src/hz_bank_rag/storage/metadata_store.py` | `_conn`, `get_kb_chunks`, `add_bad_case` 等 | SQL 参数 | 元数据持久化查询结果 |
| Milvus | `src/hz_bank_rag/storage/vector_store.py` | `MilvusVectorStore.search/search_sparse/upsert` | 向量或 query 文本 | TopK chunk 分数 |
| SiliconFlow API | `src/hz_bank_rag/core/siliconflow_client.py` | `embeddings/rerank/chat/chat_stream/vision_ocr` | texts/query/messages/image | 向量/重排分/回答文本/OCR 文本 |
| RAGAS | `src/hz_bank_rag/evaluation/ragas_runner.py` | `evaluate/evaluate_ab/evaluate_official` | dataset | 指标分数与 A/B 对照 |

## 3. 目录结构（按“调用入口 -> 执行函数”）

| 目录 | 入口文件 | 关键函数 | 主要下游 |
|---|---|---|---|
| `src/hz_bank_rag/api` | `main.py` | `build_app`, `query`, `ingest_document` | `QAService`, `RAGRepository`, `RagasRunner` |
| `src/hz_bank_rag/service` | `qa_service.py` | `ask`, `ask_stream`, `record_bad_case` | `HybridRetriever`, `SiliconFlowClient`, `MetadataStore` |
| `src/hz_bank_rag/storage` | `rag_repository.py` | `ingest_document`, `bulk_ingest`, `get_kb_chunk_map` | `parse_document`, `MetadataStore`, `VectorStore`, `BM25Store` |
| `src/hz_bank_rag/retrieval` | `hybrid_retriever.py` | `search` | `vector_store.search/search_sparse`, `bm25_store.search` |
| `src/hz_bank_rag/mcp` | `main.py` | `build_mcp_app`, `_call_tool`, `mcp_rpc` | `Runtime.qa/repo/ragas` |
| `RAG_PLUS` | `main.py` | `build_app`, `plus_query`, `run_workflow` | `AdaptiveQAExecutor`, `RedisRuntime`, `MCPRegistry`, `WorkflowEngine` |

## 4. 配置加载（非抽象，写到函数）

| 配置结论 | 证据文件 | 函数/类 | 上游 | 下游 | 入参 | 出参 |
|---|---|---|---|---|---|---|
| 主服务配置由 `HZ_RAG_*` 注入 | `src/hz_bank_rag/core/config.py` | `class Settings(BaseSettings)` + `settings = Settings()` | 模块 import 时实例化 | 被 `api/main.py`, `mcp/main.py`, `vector_store.py`, `qa_service.py` 读取 | 环境变量 | 统一配置对象 `settings` |
| RAG_PLUS 配置由 `HZ_RAG_PLUS_*` 注入 | `RAG_PLUS/config.py` | `class PlusSettings(BaseSettings)` + `plus_settings = PlusSettings()` | 模块 import 时实例化 | `RAG_PLUS/main.py`, `redis_runtime.py`, `router.py` | 环境变量 | `plus_settings` |

## 5. 外部依赖（函数级）

| 外部系统 | 对接文件 | 对接函数 | 请求入参 | 返回出参 |
|---|---|---|---|---|
| Milvus | `src/hz_bank_rag/storage/vector_store.py` | `_connect`, `search`, `search_sparse`, `upsert` | `query/kb_id/top_k` 或 `texts/chunk_ids/doc_ids` | 检索命中或写入结果 |
| SiliconFlow | `src/hz_bank_rag/core/siliconflow_client.py` | `_post`, `embeddings`, `rerank`, `chat`, `chat_stream`, `vision_ocr` | 文本/消息/图片 | 向量/分数/回答/OCR |
| Redis（RAG_PLUS） | `RAG_PLUS/redis_runtime.py` | `get_json/set_json/allow_rate/acquire_slot/release_slot` | key/value/limit | 限流判定、缓存命中、并发槽位状态 |

## 6. 核心代码 vs 辅助代码（判定依据 + 证据函数）

### 核心代码判定依据
“被线上请求路径直接调用”或“被 `build_app/build_runtime` 装配进执行链”。

| 代码 | 判定依据 | 证据函数 |
|---|---|---|
| `src/hz_bank_rag/api/main.py` | HTTP 请求直接入口 | `build_app`, `query` |
| `src/hz_bank_rag/service/qa_service.py` | `/query` 主链路核心编排 | `ask`, `_retrieve_hits`, `_generate_answer` |
| `src/hz_bank_rag/storage/rag_repository.py` | 入库/删库主流程 | `ingest_document`, `delete_kb` |
| `src/hz_bank_rag/storage/metadata_store.py` | 业务元数据持久化 | `get_kb_chunks`, `add_bad_case` |
| `src/hz_bank_rag/storage/vector_store.py` | 稠密/稀疏检索执行 | `search`, `search_sparse` |
| `src/hz_bank_rag/retrieval/*.py` | 检索策略核心逻辑 | `HybridRetriever.search`, `rerank`, `rewrite` |
| `src/hz_bank_rag/core/siliconflow_client.py` | 模型调用统一网关 | `chat`, `rerank`, `embeddings` |
| `src/hz_bank_rag/mcp/main.py` | Agent 调用入口 | `build_mcp_app`, `_call_tool` |
| `RAG_PLUS/*.py` | 增强版生产特性主链路 | `plus_query`, `AdaptiveQAExecutor.ask` |

### 辅助代码判定依据
“非请求主链路必须路径”，主要用于测试、脚本、文档、示例数据。

| 代码 | 判定依据 | 证据函数/命令 |
|---|---|---|
| `tests/*.py` | 仅测试执行时调用 | `pytest` 入口 |
| `scripts/*.ps1`, `scripts/regression_run.py` | 运维回归脚本，不在 API 热路径 | `regression_run.ps1` |
| `spec/*.md`, `docs/*.md` | 文档，不参与运行时调用 | N/A |
| `data/*` | 样例输入与评估数据目录 | `examples/seed_demo.py::seed_demo_data` 扫描读取 |

## 7. 不确定项与验证命令
- 不确定：生产是否并行部署三套服务（主 API / MCP / RAG_PLUS）。
- 验证命令：
```powershell
uvicorn hz_bank_rag.api.main:app --port 8090
uvicorn hz_bank_rag.mcp.main:app --port 8091
uvicorn RAG_PLUS.main:app --port 8092
Invoke-RestMethod http://127.0.0.1:8090/health
Invoke-RestMethod http://127.0.0.1:8091/health
Invoke-RestMethod http://127.0.0.1:8092/plus/health
```
