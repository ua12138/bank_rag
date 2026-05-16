# REQUEST_FLOW（按请求执行顺序）

## 1. 入口
- `src/hz_bank_rag/api/main.py::query`
- `src/hz_bank_rag/api/schemas.py::QueryRequest`

## 2. QAService 主链路
- `src/hz_bank_rag/service/qa_service.py::QAService.ask`

顺序：
1. `_build_memory_context`
2. `rewrite`（可跳过）
3. L3 查询
4. `kb_chunk_map`
5. `_retrieve_hits`（含 L2）
6. rerank（可跳过）
7. `_generate_answer`
8. `_save_conversation_turn`
9. L3 回写
10. 返回 response

## 3. _retrieve_hits 子链路
1. L2 查询
2. `_apply_keyword_layer`
3. `HybridRetriever.search`
4. `_apply_weak_keyword_boost`
5. `reranker.rerank`（可选）
6. `_apply_freshness_and_dedup`
7. L2 回写

## 4. 规划分支
- KG 增强（规划）
- 阶段耗时与 token 采集（规划）
