# 06｜新手可执行的排障手册

## 场景 1：`/query` 返回空答案或不相关
1. 看 `/health`：确认 `siliconflow_key_configured=true`  
   - 文件：`src/hz_bank_rag/api/main.py` -> `health()`
2. 看知识库是否为空：`/knowledge-bases/documents?kb_id=...`  
3. 强制跳过缓存：`refresh_cache=true`  
4. 切换参数试验：
   - `fast_mode=false`
   - `retrieval_scope=include_history`
   - 调整 `top_k/candidate_multiplier`

## 场景 2：入库成功但检索不到
1. 检查文档是否被识别为重复（`duplicate_exact`/近重复）  
   - 文件：`storage/rag_repository.py` -> `ingest_document()`
2. 检查切块是否为空或太短  
   - 文件：`ingestion/chunker.py` -> `split()`
3. 检查 `is_active` 与版本激活状态  
   - 文件：`storage/metadata_store.py` -> `deactivate_family_documents()`/`activate_latest_in_family()`

## 场景 3：RAG_PLUS 出现 429
1. 用户限流触发：`RedisRuntime.allow_rate()`  
2. 本地并发上限触发：`LocalConcurrencyGuard.acquire()`  
3. 分布式槽位触发：`RedisRuntime.acquire_slot()`  
   - 文件：`RAG_PLUS/main.py`、`RAG_PLUS/redis_runtime.py`

## 场景 4：MCP 工具调用报错
1. 先调用 `/tools` 看工具是否存在  
2. 用 `/mcp` 的 `tools/list` 和 `tools/call` 做最小验证  
3. 错误多发生在参数缺失或类型错误  
   - 文件：`src/hz_bank_rag/mcp/main.py` -> `_call_tool()`

## 必会 Debug 思路
```text
先判“数据有无” -> 再判“检索是否命中” -> 再判“生成是否失败”
```
