# 04｜核心模块职责表（按“你要会讲”的口径）

## API 层
- 文件：`src/hz_bank_rag/api/main.py`
- 关键函数：`build_app()`、`query()`、`ingest_document()`
- 职责：参数接收、异常映射、返回结构统一

## Service 层
- 文件：`src/hz_bank_rag/service/qa_service.py`
- 类/函数：`QAService.ask()`、`ask_stream()`、`_retrieve_hits()`
- 职责：问答总编排（改写/检索/重排/生成/缓存/记忆）

## Retrieval 层
- 文件：`src/hz_bank_rag/retrieval/hybrid_retriever.py`
- 函数：`search()`
- 职责：BM25 + 向量并行召回，RRF 融合，返回统一命中

## Storage 层
- 文件：`src/hz_bank_rag/storage/rag_repository.py`
- 函数：`ingest_document()`、`delete_document()`、`_detect_near_duplicate()`
- 职责：入库业务总控、版本管理、去重策略、索引维护

- 文件：`src/hz_bank_rag/storage/metadata_store.py`
- 类：`MetadataStore`
- 职责：SQLite 持久化（文档、分块、会话、bad case）

- 文件：`src/hz_bank_rag/storage/vector_store.py`
- 类：`InMemoryVectorStore`、`MilvusVectorStore`
- 职责：向量写入/检索/删除；Milvus 失败时降级兜底

## Ingestion 层
- 文件：`src/hz_bank_rag/ingestion/document_parser.py`
- 函数：`parse_document()` + `_parse_pdf/_parse_docx/_parse_pptx`
- 职责：多格式文档转文本

- 文件：`src/hz_bank_rag/ingestion/multimodal.py`
- 函数：`image_to_text()`
- 职责：图片 OCR 多阶段抽取

## Evaluation 层
- 文件：`src/hz_bank_rag/evaluation/ragas_runner.py`
- 类：`RagasRunner`
- 职责：轻量评估 + 官方 ragas 评估 + AB 对照

## MCP 层
- 文件：`src/hz_bank_rag/mcp/main.py`
- 函数：`_tool_specs()`、`_call_tool()`、`mcp_rpc()`
- 职责：把 HTTP RAG 能力转为工具协议

## RAG_PLUS 增强层
- 文件：`RAG_PLUS/main.py`
- 函数：`plus_query()`
- 职责：鉴权、限流、并发控制、缓存、路由编排

- 文件：`RAG_PLUS/router.py`
- 类：`SmartModelRouter`
- 职责：按复杂度和风险选模型池

- 文件：`RAG_PLUS/workflow.py`
- 类：`MixedIntentWorkflowEngine`
- 职责：混合意图拆解（qa/tool/report/action_plan）
