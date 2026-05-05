# MASTERY_TRACKER｜掌握度追踪

## 使用方法
- 每学完一个模块，把“自评”从 0-3 打分：
  - 0 = 完全不懂
  - 1 = 能复述概念
  - 2 = 能走通调用链
  - 3 = 能独立排障

## 追踪表
| 模块 | 关键文件 | 自评(0-3) | 证据（你能说出的函数） |
|---|---|---:|---|
| API 入口 | `src/hz_bank_rag/api/main.py` |  |  |
| 问答编排 | `src/hz_bank_rag/service/qa_service.py` |  |  |
| 混合检索 | `src/hz_bank_rag/retrieval/hybrid_retriever.py` |  |  |
| 入库总控 | `src/hz_bank_rag/storage/rag_repository.py` |  |  |
| 元数据 | `src/hz_bank_rag/storage/metadata_store.py` |  |  |
| 向量存储 | `src/hz_bank_rag/storage/vector_store.py` |  |  |
| 文档解析 | `src/hz_bank_rag/ingestion/document_parser.py` |  |  |
| MCP 包装 | `src/hz_bank_rag/mcp/main.py` |  |  |
| 评估模块 | `src/hz_bank_rag/evaluation/ragas_runner.py` |  |  |
| RAG_PLUS 总控 | `RAG_PLUS/main.py` |  |  |
| 智能路由 | `RAG_PLUS/router.py` |  |  |
| Workflow | `RAG_PLUS/workflow.py` |  |  |

## 里程碑定义
- M1（入门）：你能讲清 `/query` 与 `/documents` 两条链路。
- M2（可用）：你能定位“检索差/空回答/429”三类问题。
- M3（进阶）：你能解释 RAG_PLUS 为什么需要限流与路由。
- M4（面试）：你能对比基础版 vs 增强版设计取舍。
