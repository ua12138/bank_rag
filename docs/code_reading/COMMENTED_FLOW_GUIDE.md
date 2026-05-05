# BANK_RAG 注释导读（新手版）

本文对应本次补充注释的核心代码，目标是让你先看懂“这一块是干什么的”。

## 1) 项目启动链路（从进程启动到服务可用）

```text
启动 FastAPI
   |
   v
build_app() [src/hz_bank_rag/api/main.py]
   |
   +--> MetadataStore(...)      # 元数据存储（SQLite）
   +--> BM25Store()             # 关键词检索
   +--> MilvusVectorStore / InMemoryVectorStore  # 向量检索
   |
   +--> RAGRepository(...)      # 入库、分块、索引维护
   +--> HybridRetriever(...)    # BM25 + 向量融合
   +--> QAService(...)          # 问答编排
   |
   v
注册路由（/query /documents /bad-cases /evaluate ...）
```

## 2) 一次问答请求调用链路（/query）

```text
POST /query [api/main.py::query]
   |
   v
QAService.ask(...) [service/qa_service.py]
   |
   +--> 查询改写（可选，fast_mode=false 时）
   +--> 查缓存（命中则直接返回）
   +--> repo.get_kb_chunk_map(...) 取候选分块
   +--> _retrieve_hits(...)
   |      |
   |      +--> _apply_keyword_layer(...)            # 强关键词过滤（可选）
   |      +--> HybridRetriever.search(...)          # 混合检索
   |      +--> _apply_weak_keyword_boost(...)       # 弱关键词轻加分
   |      +--> reranker.rerank(...)（fast_mode=false）
   |      +--> _apply_freshness_and_dedup(...)      # 新鲜度+去重
   |
   +--> _build_memory_context(...)                  # 多轮记忆拼接/压缩
   +--> _generate_answer(...)                       # 调用大模型生成答案
   +--> _save_conversation_turn(...)                # 保存会话
   +--> 写缓存（可选）
   |
   v
返回 answer + citations + latency 等信息
```

## 3) 文档入库调用链路（/knowledge-bases/{kb_id}/documents）

```text
POST /knowledge-bases/{kb_id}/documents [api/main.py::ingest_document]
   |
   v
RAGRepository.ingest_document(...) [storage/rag_repository.py]
   |
   +--> 文件存在性校验
   +--> content_hash 精确去重
   +--> parse_document(...) 解析文本
   +--> clean_text(...) 清洗文本
   +--> _simhash_hex(...) + _detect_near_duplicate(...) 近重复检测
   +--> chunker.split(...) 分块
   +--> metadata.add_document/add_chunk(...) 写元数据
   +--> vector_store.upsert(...) 写向量库
   +--> _rebuild_bm25(...) 重建 BM25
   |
   v
返回 doc_id / chunks / 去重状态
```

## 4) 这次已补注释的文件（建议阅读顺序）

1. `src/hz_bank_rag/api/main.py`  
   重点：应用装配、路由分工、接口与服务层关系。
2. `src/hz_bank_rag/service/qa_service.py`  
   重点：问答主流程、缓存、记忆、检索后处理。
3. `src/hz_bank_rag/retrieval/hybrid_retriever.py`  
   重点：并行检索、RRF 融合、分数归一化。
4. `src/hz_bank_rag/storage/rag_repository.py`  
   重点：入库、去重、版本切换、索引维护。

## 5) 不确定项（明确标注）

- 不确定：`RAG_PLUS/` 目录是否为当前生产主入口。  
  当前注释工作基于 `src/hz_bank_rag/api/main.py` 这一套主链路完成。

