# 01｜先把项目“看成一张图”

## 你现在在学什么
这是一个“银行运维问答”RAG 系统，分两层：
- 基础层：`src/hz_bank_rag/*`（标准 API、入库、检索、评估、MCP）
- 增强层：`RAG_PLUS/*`（鉴权、限流、智能路由、工具注册、混合意图工作流）

## 一句话主流程
“文档入库 -> 切块 + 建索引 -> 查询检索 -> 大模型组织答案 -> 返回证据引用”。

## ASCII 总览图
```text
                +-----------------------------+
                |  FastAPI API (基础服务)     |
                |  src/hz_bank_rag/api/main.py|
                +--------------+--------------+
                               |
                +--------------v--------------+
                | QAService.ask / ask_stream  |
                | src/.../service/qa_service.py|
                +------+-----------+----------+
                       |           |
             +---------v--+   +---v----------------+
             | Retriever   |   | LLM Client         |
             | hybrid_...  |   | siliconflow_client |
             +----+--------+   +--------------------+
                  |
         +--------v-------------------------------+
         | RAGRepository + Metadata/BM25/Vector   |
         | storage/rag_repository.py + *_store.py |
         +----------------------------------------+
```

## 先记住 5 个核心文件
1. 启动入口：`src/hz_bank_rag/api/main.py` -> `build_app()`
2. 问答编排：`src/hz_bank_rag/service/qa_service.py` -> `class QAService`
3. 混合检索：`src/hz_bank_rag/retrieval/hybrid_retriever.py` -> `search()`
4. 入库总控：`src/hz_bank_rag/storage/rag_repository.py` -> `ingest_document()`
5. 元数据：`src/hz_bank_rag/storage/metadata_store.py` -> `class MetadataStore`
