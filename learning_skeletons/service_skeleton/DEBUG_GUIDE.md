# Service DEBUG GUIDE

1. 命中为空：检查 `repo.get_kb_chunk_map` 是否为空。  
2. 回答差：检查 `_retrieve_hits` 参数与 rerank 是否开启。  
3. 延迟高：看是否缓存未命中、是否频繁走模型调用。
