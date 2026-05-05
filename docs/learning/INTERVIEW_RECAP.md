# 最终面试复盘文档（BANK_RAG）

## 1. 项目定位（30秒）
这是一个银行运维知识问答系统。基础层负责文档入库、混合检索、答案生成和评估；增强层（RAG_PLUS）负责鉴权、限流、智能路由、工具注册和混合意图工作流。

## 2. 核心技术方案（1分钟）
- 入库：`RAGRepository.ingest_document`（文件解析->清洗->切块->向量/BM25）
- 检索：`HybridRetriever.search`（BM25+向量并行，RRF 融合）
- 生成：`QAService.ask` + `SiliconFlowClient.chat`
- 质量保障：bad case 回流 + ragas 评估

## 3. 工程亮点（1分钟）
1. 多层兜底：Milvus 不可用时可回落 InMemory  
2. 文档版本治理：family + active/inactive  
3. RAG_PLUS 的生产化控制：限流、并发舱壁、分布式槽位

## 4. 你能回答的追问
- 为什么要做 `dedup_by_family`？
- 为什么缓存 key 要带 `session_id/use_memory`？
- 为什么 RAG_PLUS 还要有 Redis 本地降级？
- 为什么 workflow 里要拆 tool_lookup/report/action_plan？

## 5. 风险与不足（诚实版）
- **不确定**：LangGraph 在该仓库中未作为主流程编排核心出现。
- 若未配置 `pytest` / 外部模型 key，无法做完整端到端自动验证。

## 6. 你的下一步提升
1. 跑通 `/demo/seed` + `/query` + `/bad-cases/ragas-dataset`
2. 手工构造一次“重复文档入库”观察 family 版本切换
3. 触发一次 RAG_PLUS 429，理解限流与并发槽位机制
