# RAG_PLUS DEBUG GUIDE

1. 401：检查 token 签名与过期时间。  
2. 403：检查 scope（`rag:query/tools:*`）。  
3. 429：检查用户限流、本地并发、分布式槽位三个阈值。  
4. 路由不符合预期：检查 `SmartModelRouter.route` 关键词与阈值。  
5. Redis 不可用：确认本地降级逻辑是否生效。
