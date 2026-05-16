# PROJECT_MAP（按运行顺序理解模块）

## 1. 启动阶段
- `src/hz_bank_rag/api/main.py::build_app`
- 初始化：MetadataStore / BM25Store / VectorStore / HybridRetriever / QAService / RagasRunner

## 2. 入库阶段
- `src/hz_bank_rag/storage/rag_repository.py::ingest_document`
- parse -> clean -> split -> metadata -> vector -> bm25

## 3. 查询阶段
- `src/hz_bank_rag/api/main.py::query`
- `src/hz_bank_rag/service/qa_service.py::ask`
- memory/rewrite -> cache -> retrieval -> rerank -> generate -> response

## 4. 职责边界
- `MetadataStore`：SQLite 元数据
- `VectorStore`：向量与 sparse 检索
- `BM25Store`：内存 sparse 兠底

## 5. 规划项
- KG 服务（规划）
- query_metrics 持久化（规划）
- `/ui/kg` `/ui/metrics`（规划）
