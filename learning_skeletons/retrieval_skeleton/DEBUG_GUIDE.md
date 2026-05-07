# Retrieval DEBUG GUIDE

1. 检索全空：检查 BM25 index 是否 rebuild、向量库是否有数据。  
2. 结果重复：检查去重策略是否在 service 层开启。  
3. 召回不稳：检查 candidate_multiplier 与 rerank 开关。
