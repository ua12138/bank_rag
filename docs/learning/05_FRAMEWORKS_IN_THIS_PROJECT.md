# 05｜框架在本项目中的“真实作用”

## FastAPI（不是抽象概念）
- 在哪里：`src/hz_bank_rag/api/main.py`、`src/hz_bank_rag/mcp/main.py`、`RAG_PLUS/main.py`
- 实际作用：
  - 声明路由
  - 请求参数校验（配合 Pydantic 模型）
  - 异常转 HTTP 状态码
  - 自动生成 Swagger

## Pydantic / pydantic-settings
- 在哪里：
  - 请求模型：`src/hz_bank_rag/api/schemas.py`、`RAG_PLUS/schemas.py`
  - 配置模型：`src/hz_bank_rag/core/config.py`、`RAG_PLUS/config.py`
- 实际作用：
  - 请求字段校验（`top_k` 范围等）
  - 环境变量注入配置

## RAG 的落地（不是框架名）
- 召回：
  - 关键词：`BM25Store.search`（`storage/bm25_store.py`）
  - 语义：`vector_store.search`（`storage/vector_store.py`）
- 融合：`HybridRetriever.search`（`retrieval/hybrid_retriever.py`）
- 生成：`SiliconFlowClient.chat`（`core/siliconflow_client.py`）

## MCP 的落地
- 在哪里：`src/hz_bank_rag/mcp/main.py`
- 实际作用：
  - 提供工具列表（`tools/list`）
  - 统一工具调用（`tools/call`）
  - 让 agent 通过协议调用 RAG 能力

## Agent/Workflow 的落地
- 在哪里：`RAG_PLUS/workflow.py`
- 实际作用：
  - 基于 query 判断意图
  - 组合“问答 + 工具搜索 + 报告”

## LangChain / LangGraph 状态
- **不确定**：当前代码中未看到 LangGraph 编排主线。
- 可确认：`langchain-text-splitters` 被用于文本切块（`ingestion/chunker.py`）。
