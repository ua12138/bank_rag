# 项目知识提取（project_intelligence）

## 1. 项目概览

项目：`hz_bank_rag`

定位：面向生产运维知识库场景的 RAG 系统，覆盖文档入库、混合检索、问答生成、bad-case 回流和 ragas 评估。

核心能力：
- 多格式解析：txt/md/log/pdf/docx/ppt/pptx/image
- 混合检索：BM25 + 向量检索 + RRF + 可选重排
- 多模态：图片 OCR + 表格识别 + CLIP 语义特征
- 质量治理：bad-case 采集、快照复现、ragas 评估
- 性能与体验：并行检索、查询缓存、多轮会话记忆

## 2. 目录与模块

- `src/hz_bank_rag/api`：FastAPI 接口层
- `src/hz_bank_rag/service`：问答编排、缓存、会话记忆
- `src/hz_bank_rag/ingestion`：文档解析、清洗、切块、多模态抽取
- `src/hz_bank_rag/retrieval`：embedding、重写、混合检索、重排
- `src/hz_bank_rag/storage`：SQLite、BM25、Milvus/InMemory
- `src/hz_bank_rag/evaluation`：ragas 评估执行
- `src/hz_bank_rag/examples`：demo 数据入库脚本

## 3. 入口与调用链

主入口：`src/hz_bank_rag/api/main.py`

启动装配：
1. `MetadataStore`（SQLite）
2. `BM25Store`
3. `MilvusVectorStore`/`InMemoryVectorStore`
4. `RAGRepository`
5. `HybridRetriever`
6. `QAService`
7. `RagasRunner`

主流程：
- 入库：解析 -> 清洗 -> 切块 -> 写元数据 -> 向量化 -> 重建 BM25
- 查询：可选重写 -> BM25 与向量并行检索 -> RRF 融合 -> 可选重排 -> 生成答案
- 评估：构建 ragas 数据集 -> 执行指标评估 -> 回归比较

## 4. Reality（真实运行视角）

### 4.1 为什么选当前模型
- Embedding：`BAAI/bge-large-zh-v1.5`，中文语义检索能力稳定。
- Rerank：`BAAI/bge-reranker-v2-m3`，对专业术语重排效果更好。
- Chat：`Qwen2.5-7B-Instruct`，成本与效果平衡。
- Vision：`Qwen2.5-VL-7B-Instruct`，用于图中文字/表格补充。

### 4.2 并发与性能
- 检索层已将 BM25 与向量检索并行化。
- `fast_mode=true` 可跳过重写/重排，优先低延迟。
- 查询缓存（TTL+LRU）可显著降低重复问题延迟。

### 4.3 数据流（线上可追踪）
- 原始文件：`data/demo_kb`（评估样例放 `data/eval_samples`，已隔离）
- 元数据：`rag_meta.db`（documents/chunks/bad_cases/conversation_messages）
- 向量：Milvus（默认 `http://47.111.101.201:19530`）

### 4.4 多轮对话
- 通过 `session_id` 写入/读取会话消息。
- 上限可配置：`conversation_max_turns/max_chars/summary_max_chars`。
- 超长时进行轻量压缩，防止上下文无限膨胀。

### 4.5 评测方式
- ragas 评估维度：faithfulness、answer_relevancy、context_precision、context_recall。
- 同时结合 bad-case 命中率做工程判定。

### 4.6 真实问题（当前已观察）
- 终端偶发中文乱码（环境编码问题）会影响排障可读性。
- ragas 当前是 LLM-as-judge 近似方案，适合内部相对对比，不等同官方完整 pipeline。
- Milvus 历史集合维度差异可能引起 collection 管理复杂度。

## 5. Audit（问题审计与改进）

### 问题 1：中文编码可读性不稳定
- 描述：部分运行输出在 PowerShell 中乱码。
- 影响：定位失败原因和日志分析效率下降。
- 优先级：P1
- 解决方案：统一 UTF-8 输出、补充编码自检脚本、规范终端编码设置。

### 问题 2：评估链路“近似 ragas”认知风险
- 描述：当前评估实现为 LLM judge 近似，团队容易误认为是官方完整 ragas。
- 影响：跨团队汇报时可能出现指标解释偏差。
- 优先级：P1
- 解决方案：文档显式标注“近似评估”；后续补官方 ragas pipeline A/B 对照。

### 问题 3：向量集合版本治理
- 描述：维度变更自动切换 collection 名，长期可能产生多套集合。
- 影响：运维复杂度上升，回溯成本高。
- 优先级：P2
- 解决方案：制定 collection 命名规范与生命周期策略（归档/清理）。

### 问题 4：回归验证自动化不足
- 描述：缺少一键“入库-问答-bad-case-ragas”回归脚本。
- 影响：变更后验证耗时，容易漏测。
- 优先级：P2
- 解决方案：增加 `scripts/regression_run.ps1` 与最小自动验收报告。

### 问题 5：测试覆盖不足
- 描述：缓存命中、会话压缩、seed 排除规则缺少单测。
- 影响：后续改动可能引入回归。
- 优先级：P2
- 解决方案：新增针对 `QAService`、`seed_demo`、`MetadataStore` 的单元测试。

## 6. 结论

这个项目已具备可运行的端到端能力，且在“性能（缓存/并行检索）+治理（bad-case/ragas）+体验（多轮会话）”方面达到可落地状态。下一阶段重点应放在：
1. 评估体系标准化
2. 回归自动化
3. 运维规范化（编码、Milvus 集合治理）
