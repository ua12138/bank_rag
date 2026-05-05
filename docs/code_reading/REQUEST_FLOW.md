# REQUEST_FLOW（`POST /query` 十步可执行追踪）

## 链路范围
- 入口：`POST /query`
- 入口函数：`src/hz_bank_rag/api/main.py::query(req: QueryRequest)`
- 目标：返回基于知识库证据的回答与 citations

---

## Step 1 / 10：HTTP 入站与参数反序列化
- 文件路径：`src/hz_bank_rag/api/main.py`
- 类名/函数名：`query(req: QueryRequest) -> dict`
- 调用关系：`FastAPI Router -> query -> QAService.ask`
- 核心入参：`QueryRequest`
- 核心出参：`dict`（后续由 `QAService.ask` 生成）
- 数据结构变化：`HTTP JSON -> QueryRequest`
- 异常/兜底：捕获 `RuntimeError`，转 `HTTPException(400)`

## Step 2 / 10：请求模型字段定义与默认值
- 文件路径：`src/hz_bank_rag/api/schemas.py`
- 类名/函数名：`class QueryRequest(BaseModel)`
- 调用关系：`query` 路由参数解析依赖该模型
- 核心入参：`kb_id/query/top_k/candidate_multiplier/fast_mode/session_id/use_memory/refresh_cache`
- 核心出参：类型化对象 `QueryRequest`
- 数据结构变化：原始字典字段补全默认值
- 异常/兜底：Pydantic 校验失败会由 FastAPI 返回 422

## Step 3 / 10：`QAService.ask` 入口与 cache key 生成
- 文件路径：`src/hz_bank_rag/service/qa_service.py`
- 类名/函数名：`QAService.ask(...)`, `_make_cache_key(...)`
- 调用关系：`api.query -> QAService.ask -> _make_cache_key`
- 核心入参：`kb_id/query/top_k/candidate_multiplier/fast_mode/session_id/use_memory`
- 核心出参：`cache_key: str`
- 数据结构变化：结构化参数 -> 单字符串 key
- 异常/兜底：无异常分支；继续下一步

## Step 4 / 10：缓存读取分支
- 文件路径：`src/hz_bank_rag/service/qa_service.py`, `src/hz_bank_rag/service/query_cache.py`
- 类名/函数名：`QAService.ask`, `QueryCache.get`
- 调用关系：`QAService.ask -> QueryCache.get`
- 核心入参：`cache_key`
- 核心出参：`cached: dict | None`
- 数据结构变化：缓存命中则 `cached` 深拷贝后追加 `cache_hit/latency/cache_stats`
- 异常/兜底：过期或未命中返回 `None`，继续检索链路

## Step 5 / 10：获取 KB chunk 映射
- 文件路径：`src/hz_bank_rag/service/qa_service.py`, `src/hz_bank_rag/storage/rag_repository.py`, `src/hz_bank_rag/storage/metadata_store.py`
- 类名/函数名：`QAService.ask -> RAGRepository.get_kb_chunk_map -> MetadataStore.get_kb_chunks`
- 调用关系：`QAService.ask -> repo.get_kb_chunk_map -> metadata.get_kb_chunks`
- 核心入参：`kb_id`
- 核心出参：`chunk_map: dict[chunk_id, {doc_id,text,metadata}]`
- 数据结构变化：`SQLite rows -> list[dict] -> dict映射`
- 异常/兜底：若 `chunk_map` 为空，直接返回固定答复“Knowledge base is empty...”

## Step 6 / 10：混合检索（稀疏+稠密）
- 文件路径：`src/hz_bank_rag/service/qa_service.py`, `src/hz_bank_rag/retrieval/hybrid_retriever.py`, `src/hz_bank_rag/storage/vector_store.py`, `src/hz_bank_rag/storage/bm25_store.py`
- 类名/函数名：`QAService._retrieve_hits`, `HybridRetriever.search`, `MilvusVectorStore.search/search_sparse`, `BM25Store.search`
- 调用关系：
  - `QAService._retrieve_hits -> HybridRetriever.search`
  - `HybridRetriever.search -> (vector_store.search_sparse OR bm25_store.search) + vector_store.search`
- 核心入参：`kb_id`, `rewritten query`, `top_k`, `candidate_multiplier`, `kb_chunk_map`
- 核心出参：`hits: list[RetrievalHit]`
- 数据结构变化：
  - `query -> sparse_hits/dense_hits (tuple列表)`
  - `tuple列表 -> rank_map -> list[RetrievalHit]`
- 异常/兜底：
  - Milvus sparse 异常时 `search_sparse` 返回空并降级（日志警告）
  - dense 检索可回退本地内存向量命中（`local_hits`）

## Step 7 / 10：可选重排分支
- 文件路径：`src/hz_bank_rag/service/qa_service.py`, `src/hz_bank_rag/retrieval/reranker.py`, `src/hz_bank_rag/core/siliconflow_client.py`
- 类名/函数名：`QAService._retrieve_hits`, `SiliconFlowReranker.rerank`, `SiliconFlowClient.rerank`
- 调用关系：`_retrieve_hits -> reranker.rerank -> client.rerank`
- 核心入参：`query`, `hits`, `top_k`
- 核心出参：重排后的 `list[RetrievalHit]`
- 数据结构变化：`hits[i].score` 叠加 `0.35 * rerank_score`
- 异常/兜底：`SiliconFlowError` 时回退为原融合分排序（不阻断）

## Step 8 / 10：上下文记忆构建与消息组装
- 文件路径：`src/hz_bank_rag/service/qa_service.py`, `src/hz_bank_rag/storage/metadata_store.py`
- 类名/函数名：`_build_memory_context`, `_compress_memory`, `_build_messages`, `MetadataStore.get_conversation_messages`
- 调用关系：`QAService.ask -> _build_memory_context -> metadata.get_conversation_messages -> _build_messages`
- 核心入参：`kb_id/session_id/use_memory/hits/query/rewritten`
- 核心出参：`memory_context: str`, `memory_meta: dict`, `messages: list[dict[str,str]]`
- 数据结构变化：会话消息列表 -> 拼接文本 ->（超长时）压缩摘要
- 异常/兜底：无历史消息时 `memory_context=''`；禁用记忆时直接返回 `enabled=False`

## Step 9 / 10：LLM 生成答案与会话持久化
- 文件路径：`src/hz_bank_rag/service/qa_service.py`, `src/hz_bank_rag/core/siliconflow_client.py`, `src/hz_bank_rag/storage/metadata_store.py`
- 类名/函数名：`_generate_answer`, `SiliconFlowClient.chat`, `_save_conversation_turn`, `add_conversation_message`, `delete_conversation_messages_before`
- 调用关系：`QAService.ask -> _generate_answer -> client.chat`; 然后 `QAService.ask -> _save_conversation_turn -> MetadataStore.*`
- 核心入参：`messages`, `model`, `session_id`, `kb_id`, `query`, `answer`
- 核心出参：`answer: str`
- 数据结构变化：`messages -> answer string`; 同步写入会话表并裁剪历史
- 异常/兜底：`chat` 抛 `SiliconFlowError` 时，返回“Model call failed + snippets”

## Step 10 / 10：响应组装与缓存写回
- 文件路径：`src/hz_bank_rag/service/qa_service.py`, `src/hz_bank_rag/api/main.py`
- 类名/函数名：`QAService.ask`, `_citation_from_hit`, `query`
- 调用关系：`QAService.ask -> _citation_from_hit (循环)`；`api.query` 直接返回该 dict
- 核心入参：`hits`, `answer`, `memory_meta`, `cache_key`
- 核心出参：HTTP 200 JSON
- 数据结构变化：
  - `RetrievalHit -> citation dict`
  - 汇总为最终响应：`{kb_id,query,rewritten_query,answer,citations,cache_hit,latency_ms,...}`
- 异常/兜底：缓存写回失败未显式捕获（依赖内存操作稳定）；接口层仅拦截 `RuntimeError`

---

## 字段级 I/O 映射表

### A. QueryRequest -> QAService.ask 参数映射

| QueryRequest 字段 | 目标函数参数 | 备注 |
|---|---|---|
| `kb_id` | `kb_id` | 知识库主键 |
| `query` | `query` | 原始用户问题 |
| `top_k` | `top_k` | 最终返回 top-k 候选 |
| `candidate_multiplier` | `candidate_multiplier` | 候选池扩展倍数 |
| `fast_mode` | `fast_mode` | 是否跳过 rewrite/rerank 部分流程 |
| `session_id` | `session_id` | 会话记忆键 |
| `use_memory` | `use_memory` | 是否注入会话历史 |
| `refresh_cache` | `refresh_cache` | 是否强制跳过缓存读取 |

### B. RetrievalHit -> citation 映射（`QAService._citation_from_hit`）

| RetrievalHit 字段 | citation 字段 | 说明 |
|---|---|---|
| `chunk_id` | `chunk_id` | 引用块 ID |
| `doc_id` | `doc_id` | 文档 ID |
| `score` | `score` | 最终排序分 |
| `bm25_score` | `bm25_score` | 稀疏分 |
| `vector_score` | `vector_score` | 稠密分 |
| `rrf_score` | `rrf_score` | RRF 融合分 |
| `rerank_score` | `rerank_score` | 重排分 |
| `metadata.file_path` | `source_file_path` | 源文件路径 |
| `metadata.file_name` | `source_file_name` | 源文件名 |
| `metadata.source_type` | `source_type` | text/image |
| `text[:220]` | `preview_text` | 证据预览 |
| `doc_id` | `asset_url` | `/knowledge-bases/documents/{doc_id}/asset` |

### C. 最终响应字段来源

| 响应字段 | 组装函数 | 原始来源 |
|---|---|---|
| `rewritten_query` | `QAService.ask` | `query` 或 `QueryRewriter.rewrite` |
| `answer` | `QAService._generate_answer` | `SiliconFlowClient.chat` 或失败兜底 |
| `citations` | `QAService._citation_from_hit` | `list[RetrievalHit]` |
| `memory` | `QAService._build_memory_context` | `conversation_messages` 表 |
| `latency_ms` | `QAService.ask` | `time.perf_counter()` 差值 |
| `cache_hit/cache_stats` | `QAService.ask` | `QueryCache.get/set/stats` |

---

## 条件分支矩阵

| 条件 | 分支逻辑 | 触发函数 | 结果 |
|---|---|---|---|
| `fast_mode=True` | 不执行 rewrite，不执行 rerank，仅截取 hits[:top_k] | `QAService.ask` + `_retrieve_hits` | 延迟更低，排序只基于 hybrid |
| `fast_mode=False` | 执行 `rewriter.rewrite` + `reranker.rerank` | `QueryRewriter.rewrite`, `SiliconFlowReranker.rerank` | 召回对齐更强，延迟更高 |
| 缓存命中 | 直接返回缓存结果并补充 `cache_hit=True` | `QueryCache.get` | 跳过检索/生成主链路 |
| 缓存未命中 | 继续走检索+生成全链路 | `QAService.ask` | 生成新答案并写回缓存 |
| KB 为空 | 直接返回固定提示文案 | `QAService.ask` | 无 citations |
| 模型调用失败 | 返回“Model call failed + snippets” | `QAService._generate_answer` | 服务可用但降级回答 |

---

## 完整调用链 ASCII（函数节点）

```text
POST /query
  -> src/hz_bank_rag/api/main.py::query(QueryRequest)
  -> src/hz_bank_rag/service/qa_service.py::QAService.ask
      -> _make_cache_key
      -> QueryCache.get (optional)
      -> RAGRepository.get_kb_chunk_map
          -> MetadataStore.get_kb_chunks [SQLite SELECT]
      -> QAService._retrieve_hits
          -> HybridRetriever.search
              -> MilvusVectorStore.search_sparse OR BM25Store.search
              -> MilvusVectorStore.search
              -> _rrf + _normalize_scores
          -> SiliconFlowReranker.rerank (if fast_mode=False)
      -> QAService._build_memory_context
          -> MetadataStore.get_conversation_messages [SQLite SELECT]
      -> QAService._build_messages
      -> QAService._generate_answer
          -> SiliconFlowClient.chat [External API]
      -> QAService._save_conversation_turn (optional)
          -> MetadataStore.add_conversation_message [SQLite INSERT]
          -> MetadataStore.delete_conversation_messages_before [SQLite DELETE]
      -> QAService._citation_from_hit
      -> QueryCache.set (optional)
  -> HTTP 200 JSON
```

---

## 不确定项与验证命令
- 不确定：外部模型是否始终返回 `choices[0].message.content` 结构（当前按此结构解析）。
- 验证命令：
```powershell
uvicorn hz_bank_rag.api.main:app --port 8090
$body = '{"kb_id":"hz-bank-demo","query":"测试问题","top_k":3,"fast_mode":true}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/query" -ContentType "application/json" -Body $body
```
