# QUESTION_BANK｜项目精读题库（含答案点）

## A. 启动与架构（10题）
1. `build_app()` 在基础服务里做了哪些装配？  
   - 答案点：`api/main.py::build_app` 初始化 meta/bm25/vector/repo/retriever/qa
2. `src/hz_bank_rag` 与 `RAG_PLUS` 的关系是什么？
3. `MCP` 在本项目里是怎么落地的？
4. 为什么要有 `Runtime` 对象（`mcp/runtime.py`）？
5. `RAG_PLUS` 为什么还要保留 `AdaptiveQAExecutor`，不直接调 `QAService.ask`？
6. `/health` 对排障有什么价值？
7. Milvus 与 InMemory 如何切换？
8. 为什么 `seed_demo` 要排除 `eval_samples`？
9. 本项目有哪些“可独立启动”的服务？
10. 如果只让你选3个入口文件精读，你选哪3个？

## B. 请求链路（12题）
1. `/query` 的完整调用链是什么？
2. `QAService.ask` 的缓存 key 包含哪些维度？
3. `fast_mode` 对检索流程影响在哪里？
4. `_retrieve_hits` 内做了哪几层处理？
5. 为什么先宽召回（candidate_k）再收缩 top_k？
6. RRF 融合解决了什么问题？
7. memory 在哪里组装，怎么压缩？
8. 为什么会话消息要裁剪旧数据？
9. `/query/stream` 与 `/query` 最大差异是什么？
10. 如果模型调用失败，系统如何兜底？
11. `retrieval_scope=active_only` 与 `include_history` 差异？
12. `dedup_by_family=true` 的业务意义？

## C. 入库与存储（12题）
1. 文档入库完整步骤？
2. `content_hash` 与 `near_hash` 各自解决什么问题？
3. `doc_family_id` 如何参与版本管理？
4. 删除文档后为什么要“回激活”历史版本？
5. 为什么 BM25 需要重建？
6. `MetadataStore` 管哪些表？
7. bad case 如何转成 ragas 数据集？
8. conversation 表为什么按 `id desc` 拉取再 reverse？
9. 向量库写入失败时还有哪些兜底？
10. Milvus 稀疏检索不可用会怎样？
11. 文档解析支持哪些格式？
12. 图片 OCR 走几级策略？

## D. RAG_PLUS 增强能力（10题）
1. 429 可能由哪三层控制触发？
2. 智能路由如何计算复杂度？
3. risky 路由有什么特殊处理？
4. 工具注册中心搜索分数怎么构成？
5. scope 如何控制工具可见性？
6. workflow 如何判断混合意图？
7. report 是在 workflow 哪一步生成？
8. redis 不可用时系统如何降级？
9. token 的签名与校验机制是什么？
10. 为什么 `/plus/query` 还做了缓存？
