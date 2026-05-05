# 03｜请求调用链路（最重要）

## 链路 1：`POST /query`
- 路由：`src/hz_bank_rag/api/main.py` -> `query()`
- 核心函数：`src/hz_bank_rag/service/qa_service.py` -> `QAService.ask()`

### 详细步骤
1. 查询改写（`QueryRewriter.rewrite`，fast_mode 可跳过）  
2. 计算 cache key（`_make_cache_key`）并查缓存  
3. 拉取候选 chunk（`RAGRepository.get_kb_chunk_map`）  
4. 检索（`QAService._retrieve_hits`）  
5. （可选）重排（`SiliconFlowReranker.rerank`）  
6. 组装 memory（`_build_memory_context`）  
7. 生成答案（`_generate_answer` -> `SiliconFlowClient.chat`）  
8. 保存会话（`_save_conversation_turn`）  
9. 返回 answer + citations + latency

## 链路 2：`POST /knowledge-bases/{kb_id}/documents`
- 路由：`src/hz_bank_rag/api/main.py` -> `ingest_document()`
- 核心函数：`src/hz_bank_rag/storage/rag_repository.py` -> `ingest_document()`

### 详细步骤
1. 文件存在性检查  
2. `content_hash` 精确去重  
3. `parse_document` 文档解析  
4. `clean_text` 清洗  
5. `simhash` 近重复检查（可拒绝）  
6. `Chunker.split` 切块  
7. 写入 `documents/chunks`（`MetadataStore`）  
8. 写入向量库（`vector_store.upsert`）  
9. 重建 BM25（`_rebuild_bm25`）

## 链路 3：RAG_PLUS `/plus/query`
- 路由：`RAG_PLUS/main.py` -> `plus_query()`
- 新增步骤：
  - token 验证（`AuthService`）
  - 用户限流（`RedisRuntime.allow_rate`）
  - 本地+分布式并发槽位控制（`LocalConcurrencyGuard` + `RedisRuntime.acquire_slot`）
  - 智能路由选模型（`SmartModelRouter.route`）
  - 自适应问答（`AdaptiveQAExecutor.ask`）

## ASCII 请求图
```text
/query
 -> QAService.ask
 -> _retrieve_hits
 -> HybridRetriever.search
 -> _generate_answer
 -> return

/documents
 -> RAGRepository.ingest_document
 -> parse/clean/chunk
 -> metadata + vector + bm25
 -> return
```
