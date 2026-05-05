# DEV_SPEC（中文技术说明）

## 1. 文档目的

本文件面向开发与维护人员，描述系统真实实现、核心调用链、评估与回归机制，并整理本轮用户问题的逐项答案。

## 2. 模块分层

- `src/hz_bank_rag/api/`：HTTP API 层（FastAPI）
- `src/hz_bank_rag/mcp/`：MCP 封装服务（供 Agent 工具化调用）
- `src/hz_bank_rag/service/`：问答编排（检索串联、缓存、会话记忆、bad-case）
- `src/hz_bank_rag/ingestion/`：文档解析、清洗、切块、多模态 OCR
- `src/hz_bank_rag/retrieval/`：Embedding、混合检索、Query Rewrite、Rerank
- `src/hz_bank_rag/storage/`：SQLite 元数据、Milvus 向量库（稠密+稀疏 BM25）、内存 BM25 兜底
- `src/hz_bank_rag/evaluation/`：RAGAS 轻量/官方/A-B 评估

## 3. 核心链路

### 3.1 入库链路

文档 -> 解析 -> 清洗 -> 切块 -> 元数据写入 SQLite -> Embedding -> 向量写入 Milvus/InMemory -> Milvus 稀疏 BM25（优先）/内存 BM25（兜底）。

重复入库校验（默认启用）：
- 同一 `kb_id` 下按 `file_path` 去重。
- 同一 `kb_id` 下按文件内容 `SHA256` 去重（跨文件名重复也会拦截）。
- 单文件入库重复返回冲突；批量入库会跳过重复并返回 `skipped_duplicates`。

代码入口：
- `src/hz_bank_rag/storage/rag_repository.py`
- `src/hz_bank_rag/ingestion/document_parser.py`
- `src/hz_bank_rag/ingestion/chunker.py`

### 3.2 查询链路

`/query` 或 `/query/stream` ->（可选 Rewrite）-> BM25 + Vector 并行召回 -> RRF 融合 ->（非 fast_mode 时 Rerank）-> LLM 生成。

稀疏召回来源：
- 优先：Milvus 稀疏 BM25（持久化）
- 兜底：`rank_bm25` 内存索引（仅在 Milvus 稀疏不可用时使用）

代码入口：
- `src/hz_bank_rag/service/qa_service.py`
- `src/hz_bank_rag/retrieval/hybrid_retriever.py`
- `src/hz_bank_rag/retrieval/reranker.py`

## 4. 本轮问题总览（逐题整理）

### 4.1 RAGAS 是否必须参考答案，为什么项目里要用数据集

- 结论：RAGAS 不是所有指标都强依赖 `ground_truth`，但项目要做“可回归、可对比、可复现”，必须用固定数据集。
- 原因：
  - `context_recall` 等指标天然依赖 ground truth。
  - 需要稳定比较“优化前 vs 优化后”“lightweight vs official”。
  - 需要 bad-case 回灌后的回归验证。
- 相关接口：
  - `POST /evaluate/ragas`
  - `POST /evaluate/ragas/official`
  - `POST /evaluate/ragas/ab`
  - `POST /evaluate/ragas/dataset/build`

### 4.2 项目如何支持 txt/md/log/pdf/doc/docx/ppt/pptx/图片 多格式解析

- `parse_document()` 依据后缀分发：
  - 文本：`.txt/.md/.log/.csv`
  - PDF：同页双通道，正文抽取与页内图片 OCR 同时执行
  - Word：`.docx` 解析段落和表格；`.doc` 通过 COM
  - PPT：`.pptx` 提取 shape 文本；`.ppt` 通过 COM
  - 图片：直接走多阶段 OCR 管线
- 代码：`src/hz_bank_rag/ingestion/document_parser.py`

补充说明（PDF 图文关联）：
- 每页正文标记为 `[pdf-page-N-text]`
- 每张图片 OCR 标记为 `[pdf-page-N-image-M-ocr]`
- 下游切块会保留页号和图片序号标记，用于检索结果定位和答案证据归因。

### 4.3 RapidOCR + pytesseract + 视觉模型 OCR + CLIP 各自作用与引入原因

- RapidOCR：本地 OCR 第一阶段，中文识别稳定性较好。
- pytesseract：本地 OCR 兜底，补 RapidOCR 漏检。
- 视觉模型 OCR（SiliconFlow VL）：处理复杂版式、弱扫描件与图片内语义结构。
- 表格优先提取：先给“表格优先”提示词，再 fallback 到通用 OCR。
- CLIP：输出图像向量摘要，补充多模态语义线索（当前为文本补充信号）。
- 代码：`src/hz_bank_rag/ingestion/multimodal.py`

### 4.4 BM25 是什么，为什么要用

- BM25 是稀疏检索（关键词检索）方法，擅长术语、缩写、精确词匹配。
- 与向量检索互补：向量检索擅长语义近似，BM25 保证关键词命中能力。
- 落地方式：Milvus 稀疏 BM25 持久化优先，内存 BM25 作为兜底。
- 代码：
  - `src/hz_bank_rag/storage/vector_store.py`
  - `src/hz_bank_rag/storage/bm25_store.py`

### 4.5 RRF 融合是什么

- RRF（Reciprocal Rank Fusion）按“排名位置”融合多路检索结果：
  - `1 / (k + rank)`，对不同分数尺度鲁棒。
- 当前实现：BM25 排名分 + 向量排名分，再叠加少量归一化分打破平分。
- 代码：`src/hz_bank_rag/retrieval/hybrid_retriever.py`

### 4.6 如何进行 rerank（精排）

- 非 `fast_mode` 时，召回候选集送入 SiliconFlow `/rerank`。
- 返回相关性后与融合分做线性组合：`final = hybrid + 0.35 * rerank`。
- rerank 失败自动降级为融合分排序，保障可用性。
- 代码：`src/hz_bank_rag/retrieval/reranker.py`

### 4.7 Bad Case 在项目里如何运行

- 收集入口：`POST /bad-cases`
- 自动快照：可自动抓取当前 query 的检索快照（top_hits）。
- 存储：SQLite `bad_cases` 表（含类别、严重性、状态、期望答案）。
- 回流：`GET /bad-cases/ragas-dataset` 可转为评估集。
- 代码：
  - `src/hz_bank_rag/service/qa_service.py`
  - `src/hz_bank_rag/storage/metadata_store.py`
  - `src/hz_bank_rag/api/main.py`

### 4.8 项目如何进行 RAGAS 评估

- `lightweight`：LLM Judge 打分四指标，依赖少、速度快。
- `official`：调用官方 ragas（需要额外依赖）。
- `ab`：同数据集双跑，输出指标差值。
- 四指标：
  - `faithfulness`：答案是否有上下文证据支撑
  - `answer_relevancy`：答案是否直接回答问题
  - `context_precision`：召回上下文噪声是否低
  - `context_recall`：召回上下文是否覆盖 ground truth 关键事实
- 代码：`src/hz_bank_rag/evaluation/ragas_runner.py`

### 4.9 项目如何优化（检索与问答时延）

- 并行召回（BM25 + 向量）
- `fast_mode` 跳过 Rewrite 与 Rerank
- SSE 流式输出：`POST /query/stream`
- Query Cache（TTL + LRU）
- Milvus 维度变化自动切换 collection，降低异常中断
- 代码：
  - `src/hz_bank_rag/service/qa_service.py`
  - `src/hz_bank_rag/service/query_cache.py`
  - `src/hz_bank_rag/storage/vector_store.py`

### 4.10 项目如何进行查询缓存

- 类型：进程内内存缓存（`OrderedDict`）
- 策略：TTL + LRU
- Key：`kb_id|query|rewritten|top_k|candidate_multiplier|fast_mode|session_id|use_memory`
- 失效：bad-case 写入后按 `kb_id` 前缀失效
- 代码：`src/hz_bank_rag/service/query_cache.py`

### 4.11 项目如何进行上下文优化（会话记忆）

- 开关：`use_memory` + `session_id`
- 落库：`conversation_messages` 表
- 记忆窗口：`conversation_max_turns`（默认 8 轮）
- 长度限制：`conversation_max_chars`（默认 3000）
- 压缩策略：保留最近消息，长句做首尾裁剪，最终截断至 `conversation_summary_max_chars`（默认 800）
- 清理策略：每轮保存后清理过旧消息
- 代码：
  - `src/hz_bank_rag/service/qa_service.py`
  - `src/hz_bank_rag/storage/metadata_store.py`

### 4.12 模型输入长度限制与项目内约束

- 模型侧：由 SiliconFlow 对应模型决定上下文窗口。
- 项目侧：
  - Embedding 批大小限制：`siliconflow_embedding_batch_size=32`
  - 生成输出上限：`siliconflow_chat_max_tokens=1024`
  - Milvus 文本字段截断：`text[:8192]`
- 代码：
  - `src/hz_bank_rag/core/config.py`
  - `src/hz_bank_rag/core/siliconflow_client.py`
  - `src/hz_bank_rag/storage/vector_store.py`

### 4.13 视觉模型 OCR 用的具体模型、用途、表格区分方式

- 当前视觉模型：`Qwen/Qwen2.5-VL-7B-Instruct`（配置项 `siliconflow_vision_model`）
- 用途：复杂图片 OCR、扫描件补偿、表格提取增强
- 表格区分：先走“表格优先提示词”，若返回结果中存在 Markdown 表格特征（如 `|`、`---`）即视为表格提取成功，否则回退通用 OCR
- 代码：
  - `src/hz_bank_rag/core/config.py`
  - `src/hz_bank_rag/ingestion/multimodal.py`

### 4.14 是否使用 Cross-Encoder 精排

- 已使用“Cross-Encoder 思路”的 Rerank 精排阶段。
- 当前模型：`BAAI/bge-reranker-v2-m3`（SiliconFlow Rerank API）
- 位置：召回之后、生成之前。
- 代码：
  - `src/hz_bank_rag/retrieval/reranker.py`
  - `src/hz_bank_rag/core/config.py`

## 5. Milvus Collection 命名与生命周期

- 当前运行版本：
  - Milvus Server：`2.6.9`
  - `pymilvus`：`2.6.11`
- 命名规则：`<base>__<embedding_model_slug>__d<dim>__hbm25`
- 目标：维度变化或模型切换时自动隔离，避免脏数据混用
- 迁移策略：若存在旧版 dense-only collection（无 `__hbm25` 后缀），系统会在首次启动时尝试自动迁移到新 collection。
- 生命周期接口：
  - `GET /collections/policy`
  - `GET /collections/managed`
  - `POST /collections/cleanup`
- 建议：先 `dry_run=true`，确认后再 `dry_run=false`

## 6. MCP 封装服务

入口：`src/hz_bank_rag/mcp/main.py`

工具用途：为后续 Agent 提供稳定调用层，避免直接绑定业务 API 细节。当前支持健康检查、入库、问答、bad-case 提交、RAGAS A/B 等工具。

## 7. 自动化回归与测试

- 回归脚本：
  - `scripts/regression_run.ps1`
  - `scripts/regression_run.py`
- 报告输出：
  - `reports/regression_report_*.json`
  - `reports/regression_report_*.md`
- 单元测试：
  - `tests/test_qa_service.py`
  - `tests/test_seed_demo.py`
  - `tests/test_metadata_store.py`
  - `tests/test_mcp_wrapper.py`
  - `tests/test_smoke.py`

## 8. RAG_PLUS 增强版

新增独立目录：`RAG_PLUS/`，用于承载高并发、智能路由、企业级 MCP、混合意图、鉴权与 Redis 负载优化能力。

详细架构说明见：
- `spec/RAG_PLUS_SPEC.md`

## 9. 入库与召回优化专项（本次新增）

### 9.1 入库侧：关键词抽取 + 版本化 + 三层去重

调用链（函数级）：
- `src/hz_bank_rag/storage/rag_repository.py::ingest_document`
  - `parse_document` -> `clean_text`
  - `extract_keywords`（文档级关键词）
  - `Chunker.split`
  - `extract_chunk_keywords`（块级关键词）
  - `MetadataStore.add_document`（写入版本字段）
  - `vector_store.upsert` / `_rebuild_bm25`

新增字段（`documents` 表）：
- `doc_family_id`：同文档族标识
- `version_no`：版本号（同族递增）
- `effective_at`：生效时间
- `is_active`：当前有效版本
- `content_hash`：内容哈希（用于幂等）
- `near_hash`：SimHash（用于近重复检测）
- `keywords_json`：文档关键词

三层去重策略：
1. `exact duplicate`：`content_hash` 命中即幂等返回（不重复向量化）
2. `near duplicate`：`_simhash_hex` + 汉明距离阈值（配置 `near_duplicate_hamming_threshold`）
3. `same family update`：新版本入库前 `deactivate_family_documents`，新文档置 `is_active=1`

### 9.2 召回侧：关键词层 + Hybrid + Rerank + 新鲜度去重

调用链（函数级）：
- `src/hz_bank_rag/service/qa_service.py::ask`
  - `_retrieve_hits`
    - `_apply_keyword_layer`（强/弱关键词）
    - `HybridRetriever.search`（BM25 + Dense + RRF）
    - `_apply_weak_keyword_boost`
    - `SiliconFlowReranker.rerank`（非 fast_mode）
    - `_apply_freshness_and_dedup`（新鲜度 + 同族去重）

查询新增参数：
- `retrieval_scope`: `active_only | include_history`
- `freshness_weight`: 新鲜度权重
- `dedup_by_family`: 是否按 `doc_family_id` 折叠

默认策略：
- `retrieval_scope=active_only`
- `dedup_by_family=true`
- `freshness_weight=0.08`

### 9.3 关键词层与 BM25 的边界

- 关键词层（`QAService._apply_keyword_layer`）：
  - 目标：业务约束（必须词/强约束）
  - 输出：候选集过滤与弱加分特征
- BM25（`HybridRetriever.search` 内稀疏召回）：
  - 目标：全文词项相关性排序
  - 输出：稀疏相关性分值

组合关系：
- 先关键词层过滤候选范围
- 再 BM25 + Dense 混合召回
- 最后 Rerank 与新鲜度去重

### 9.4 ASCII 链路图

```text
Ingest:
file
  -> parse_document()
  -> clean_text()
  -> extract_keywords()                # doc_keywords
  -> Chunker.split()
  -> extract_chunk_keywords()          # chunk_keywords
  -> MetadataStore.add_document()      # family/version/active/hash
  -> vector_store.upsert()
  -> BM25 rebuild

Query:
POST /query
  -> QAService.ask()
  -> _apply_keyword_layer()
  -> HybridRetriever.search()          # BM25 + Dense + RRF
  -> reranker.rerank()                 # non-fast mode
  -> _apply_freshness_and_dedup()
  -> LLM generate
  -> response(citations with family/version metadata)
```
