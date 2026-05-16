# DEV_SPEC（按操作顺序的技术说明）

## 1. 服务装配顺序
入口：`src/hz_bank_rag/api/main.py::build_app`
1. `MetadataStore`
2. `BM25Store`
3. `VectorStore`（Milvus/InMemory）
4. `HybridRetriever`
5. `QAService`
6. `RagasRunner`

## 2. 入库链路
入口：`src/hz_bank_rag/storage/rag_repository.py::ingest_document`
- 去重 -> 解析 -> 清洗 -> 切块 -> 元数据入库 -> 向量入库 -> BM25 更新

## 3. 查询链路
入口：`src/hz_bank_rag/api/main.py::query`
核心：`src/hz_bank_rag/service/qa_service.py::ask`
- memory -> rewrite -> L3 -> chunk_map -> _retrieve_hits -> rerank -> generate -> save_conversation -> L3 回写

## 4. 检索链路
入口：`src/hz_bank_rag/retrieval/hybrid_retriever.py::search`
- sparse -> dense -> RRF -> `RetrievalHit[]`

## 5. 缓存与失效
- L1 `EmbeddingCache`
- L2 `RetrievalCache`
- L3 `AnswerCache`
- 文档变更后按 `kb_id` 失效 L2/L3

## 6. 规划项
- KG：`/kg/*`，`enable_kg`，`kg_hop_limit`，`kg_citations`
- Metrics：`/metrics/*`，`rewrite_ms/retrieval_ms/rerank_ms/llm_ms/total_ms`
- UI：`/ui/kg`，`/ui/metrics`

## 7. 不确定项
- `SiliconFlowClient.chat` 当前代码路径未显式返回 usage 字段。


- RAG_PLUS ?? `enable_kg` / `kg_hop_limit` ?????
