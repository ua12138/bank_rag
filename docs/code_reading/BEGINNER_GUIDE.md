# BEGINNER_GUIDE（开发小白版）

这份文档基于你已经有的三份“函数级证据”文档：
- `docs/code_reading/PROJECT_MAP.md`
- `docs/code_reading/STARTUP_FLOW.md`
- `docs/code_reading/REQUEST_FLOW.md`

目标：让你从“看不懂项目”到“能独立讲清主链路、能定位问题”。

---

## 一、先看什么、再看什么、最后看什么

## 第 1 步（先看）：`PROJECT_MAP.md`
先回答三个最基础问题：
1. 这个项目是干什么的？
2. 主要有哪些模块？
3. 每个模块由哪个函数负责？

你需要重点盯住这几行（函数名）：
- `src/hz_bank_rag/api/main.py::build_app`
- `src/hz_bank_rag/service/qa_service.py::QAService.ask`
- `src/hz_bank_rag/storage/rag_repository.py::RAGRepository.ingest_document`
- `src/hz_bank_rag/retrieval/hybrid_retriever.py::HybridRetriever.search`

看完的标准：
- 你能说出“问答链路核心在哪个函数”
- 你能说出“入库链路核心在哪个函数”

## 第 2 步（再看）：`STARTUP_FLOW.md`
再回答“服务怎么活起来”的问题：
1. 启动命令是什么？
2. `uvicorn` 启动后，先调用哪个函数？
3. 哪些组件在启动时被构造？

你要重点看三条入口：
- 主 API：`uvicorn hz_bank_rag.api.main:app`
- MCP：`uvicorn hz_bank_rag.mcp.main:app`
- RAG_PLUS：`uvicorn RAG_PLUS.main:app`

看完的标准：
- 你能讲清：`uvicorn -> build_app -> 组件初始化 -> 路由注册`
- 你能讲清三套服务各自职责

## 第 3 步（最后看）：`REQUEST_FLOW.md`
最后进入“最重要的一条业务链”：`POST /query`。

你要按 10 步逐条过：
- 参数怎么进来
- 怎么查缓存
- 怎么查 chunk
- 怎么混合检索
- 怎么重排
- 怎么拼 prompt
- 怎么调模型
- 怎么落会话
- 怎么返回结果

看完的标准：
- 你可以不看代码，直接口述完整调用链
- 你能指出每一步对应哪个函数

---

## 二、关键技术名词（小白解释 + 本项目中的作用）

| 技术名词 | 小白解释 | 本项目里具体作用 | 代码位置（证据） |
|---|---|---|---|
| RAG（Retrieval-Augmented Generation） | 先“查资料”，再“让大模型回答” | 先从知识库检索证据，再把证据喂给模型生成答案 | `QAService.ask` + `HybridRetriever.search` |
| FastAPI | Python Web 框架，负责提供 HTTP 接口 | 定义 `/query`、`/knowledge-bases/*`、`/evaluate/*` 等接口 | `src/hz_bank_rag/api/main.py::build_app` |
| Uvicorn | ASGI 服务启动器 | 运行 `app`，让 API 能被访问 | 启动命令见 `STARTUP_FLOW.md` |
| Pydantic | 请求/响应数据校验与类型化 | 把 JSON 转成 `QueryRequest` 等对象，校验字段 | `src/hz_bank_rag/api/schemas.py` |
| SQLite | 轻量关系型数据库 | 存文档元数据、chunks、bad-case、会话消息 | `src/hz_bank_rag/storage/metadata_store.py` |
| Milvus | 向量数据库 | 存储向量并执行稠密向量检索，支持 sparse BM25 检索 | `src/hz_bank_rag/storage/vector_store.py` |
| Embedding（向量化） | 把文本变成向量（数字数组） | 用向量相似度做语义检索 | `SiliconFlowClient.embeddings` + `MilvusVectorStore.search` |
| BM25 | 关键词检索算法（偏“字面匹配”） | 作为稀疏检索，与向量检索互补 | `BM25Store.search` 或 `MilvusVectorStore.search_sparse` |
| 稠密检索（Dense Retrieval） | 用向量距离找“语义接近”文本 | 找到表达不同但意思接近的 chunk | `MilvusVectorStore.search` |
| 稀疏检索（Sparse Retrieval） | 用词项匹配找“关键词命中”文本 | 对术语、告警码、固定词更稳 | `BM25Store.search` / `search_sparse` |
| RRF（Reciprocal Rank Fusion） | 多个检索结果做排名融合 | 把稀疏和稠密结果合并成一个稳定排序 | `HybridRetriever._rrf` + `search` |
| Rerank（重排） | 对候选结果做二次精排 | 提高最终 top-k 证据质量 | `SiliconFlowReranker.rerank` |
| Query Rewrite | 把口语问题改写成更适合检索的问题 | 提升召回质量（尤其运维术语） | `QueryRewriter.rewrite` |
| Chunking（切块） | 长文拆成小块 | 便于检索和向量化，降低噪声 | `Chunker.split`（在 `RAGRepository.ingest_document` 中调用） |
| OCR | 图片转文字 | 解析图片/扫描件/PDF里的图像文字 | `ingestion/multimodal.py` |
| VLM（Vision-Language Model） | 能看图并理解文字/表格的模型 | OCR 补充，优先抽表格，再抽通用文字 | `_ocr_table_with_vision_model` |
| CLIP | 图文同空间特征模型 | 产出图像语义特征摘要，增强多模态线索 | `_clip_image_embedding` |
| Query Cache | 问答结果缓存 | 相同问题短时间内直接返回，降延迟 | `QueryCache.get/set` |
| 会话记忆（Conversation Memory） | 保存上下文对话历史 | 多轮问答时补充上下文，并做压缩 | `_build_memory_context` |
| Bad Case | 用户反馈的失败样例 | 问题追踪与后续检索/Prompt优化输入 | `QAService.record_bad_case` |
| RAGAS | RAG 评估框架 | 评估回答忠实度、相关性、上下文质量 | `RagasRunner.evaluate_ab` |
| MCP | 给 Agent 调用的工具协议封装 | 把 `rag.query` 等能力包装成工具 | `src/hz_bank_rag/mcp/main.py` |
| JSON-RPC | 一种标准化调用格式 | MCP 的 `/mcp` 用它处理 `initialize/tools/call` | `mcp_rpc` |
| Redis（RAG_PLUS） | 内存数据库 | 做分布式缓存、限流、并发槽位控制 | `RAG_PLUS/redis_runtime.py` |
| 限流（Rate Limit） | 控制单位时间请求量 | 防止某个用户压垮服务 | `RedisRuntime.allow_rate` |
| 并发槽位（Inflight Slot） | 控制同时处理的请求数 | 防止瞬时高并发拖垮实例 | `acquire_slot/release_slot` |

---

## 三、把三份文档串成一个“完整脑图”

你可以用下面这句话总结全项目：

1. `PROJECT_MAP` 告诉你“有哪些角色（模块）”。
2. `STARTUP_FLOW` 告诉你“这些角色如何在启动时被组装起来”。
3. `REQUEST_FLOW` 告诉你“真正来一个请求时，这些角色按什么顺序协作”。

对应到主链路：
- 入口：`api/main.py::query`
- 编排：`QAService.ask`
- 证据：`HybridRetriever.search`
- 精排：`SiliconFlowReranker.rerank`
- 生成：`SiliconFlowClient.chat`
- 返回：`QAService.ask` 组装 response

---

## 四、7 天吃透这个项目（可执行学习计划）

## Day 1：先搭建全局认知
- 读：`PROJECT_MAP.md` 全文
- 目标：记住 10 个核心函数名
- 输出：手写一张“模块 -> 核心函数”表

## Day 2：搞懂启动过程
- 读：`STARTUP_FLOW.md`
- 跑：
  - `uvicorn hz_bank_rag.api.main:app --port 8090`
  - `GET /health`
- 目标：能口述主 API 启动链
- 输出：画一张 `uvicorn -> build_app -> route` 小图

## Day 3：吃透主请求链路
- 读：`REQUEST_FLOW.md` 的 10 步
- 跑：`POST /query`
- 目标：知道每一步的入参/出参
- 输出：自己写一版 10 步摘要（每步 1 句）

## Day 4：专攻检索质量
- 读源码：
  - `hybrid_retriever.py`
  - `reranker.py`
  - `query_rewrite.py`
- 目标：讲清 BM25 + Dense + RRF + Rerank 为什么一起用
- 输出：写 5 条“检索质量提升点”

## Day 5：专攻入库与解析
- 读源码：
  - `rag_repository.py`
  - `document_parser.py`
  - `multimodal.py`
- 目标：讲清从文件到 chunk 到向量的全流程
- 输出：画“入库链路图”（含去重、切块、upsert）

## Day 6：专攻评估与闭环
- 读源码：
  - `ragas_runner.py`
  - `qa_service.py` 里的 `record_bad_case`
- 跑：`/bad-cases`、`/evaluate/ragas/ab`
- 目标：讲清“问题反馈如何反哺优化”
- 输出：写 1 页《Bad Case -> RAGAS -> 优化动作》

## Day 7：专攻增强能力（RAG_PLUS + MCP）
- 读源码：
  - `RAG_PLUS/main.py`
  - `RAG_PLUS/redis_runtime.py`
  - `src/hz_bank_rag/mcp/main.py`
- 目标：讲清鉴权、限流、缓存、工具封装
- 输出：做一次 20 分钟项目讲解（自己录音复盘）

---

## 五、学习完成判定（你是否真的吃透）

满足以下 5 条，说明你已经能独立维护这套系统：
1. 不看文档，能口述 `POST /query` 10 步链路。 
2. 能解释每个核心技术名词在本项目中的作用（不是教科书定义）。
3. 遇到“回答慢/答非所问/命中差”，能定位到具体函数排查。 
4. 能自己新增一个 MCP tool（仿照 `rag.query`）。
5. 能解释主 API、MCP、RAG_PLUS 三者分工。

---

## 六、你关心的“近似文件 + 关键词层”怎么评估

已落地可执行评估：

1. 脚本入口：`scripts/perf_ab_eval.ps1`
2. 核心实现：`scripts/perf_ab_eval.py`
3. 样例问题集：`data/eval_samples/perf_queries.json`
4. 详细说明：`docs/code_reading/PERF_AB_EVAL.md`

运行命令：

```powershell
.\scripts\perf_ab_eval.ps1 -KbId hz-bank-demo -Concurrency 20 -Rounds 3
```

你会拿到：
- A/B 两组的 `P50/P95/P99/QPS`
- TopK 重复证据率变化
- 最新文档命中率变化
- Precision@K 代理指标变化
