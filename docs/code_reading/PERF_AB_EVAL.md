# 中等并发场景性能评估（近似文件打分 + 关键词层）

本文是“可执行版”评估方案，目标是回答两件事：
1. 近似文件打分 + 最新优先，实际能提升多少检索质量。
2. 关键词层引入后，时延到底是下降还是上升。

## 1. 评估口径

- 并发：20
- 数据规模：约 50k chunks（目标口径）
- 基线链路（A 组）：
  - `rewrite -> hybrid -> rerank`
  - 对应函数：`src/hz_bank_rag/retrieval/hybrid_retriever.py::HybridRetriever.search`
  - 对应函数：`src/hz_bank_rag/retrieval/reranker.py::SiliconFlowReranker.rerank`
- 优化链路（B 组）：
  - `rewrite -> keyword layer -> hybrid -> rerank -> family dedup + freshness`
  - A/B 评估实现文件：`scripts/perf_ab_eval.py`

## 2. 估算区间（静态量级）

相对“什么都不做”的基线：

1. 关键词层（query 前置过滤）
- 固定开销：`+2 ~ +8 ms/请求`
- 关键词有效时：
  - Hybrid 耗时下降：`10% ~ 25%`
  - Rerank 耗时下降：`15% ~ 35%`
  - 端到端 P95：`净下降 8% ~ 22%`
- 关键词无效时：
  - 端到端 P95：`可能上升 1% ~ 6%`

2. 近似文件打分 + 最新优先
- 查询侧开销：`+1 ~ +5 ms/请求`
- Top5 重复证据率：`下降 30% ~ 70%`
- Precision@5：`提升 8% ~ 20%`
- 最新版本命中率：`60%~75% -> 90%+`（依赖版本字段质量）

3. 关键词层 vs BM25（本项目语义）
- BM25：相关性排序器（软约束），函数入口：`HybridRetriever.search` 内的 `bm25_store.search` / `vector_store.search_sparse`
- 关键词层：业务过滤器（硬/半硬约束），实现位置：`scripts/perf_ab_eval.py::_keyword_filter`
- 叠加收益：先减候选，再做 BM25+向量排序，尾延迟更稳。

## 3. 可复现实测（已落地脚本）

### 3.1 输入样例

- 查询样例文件：`data/eval_samples/perf_queries.json`
- 每条样例结构：
  - `query`：问题文本
  - `expected_keywords`：质量代理指标的匹配词（用于 `precision_at_k_proxy`）

### 3.2 执行命令

```powershell
.\scripts\perf_ab_eval.ps1 -KbId hz-bank-demo -Concurrency 20 -Rounds 3
```

或：

```powershell
python scripts/perf_ab_eval.py --kb-id hz-bank-demo --queries-file data/eval_samples/perf_queries.json --concurrency 20 --rounds 3 --use-rerank
```

### 3.3 输出报告

- `reports/perf_ab_report_*.json`
- `reports/perf_ab_report_*.md`

## 4. 指标定义（脚本中的真实实现）

实现文件：`scripts/perf_ab_eval.py`

1. 性能指标
- `P50/P95/P99`：单请求耗时分位数（毫秒）
- `QPS`：每组请求吞吐

2. 质量指标
- `duplicate_rate_avg`：TopK 同族重复率，函数：`_quality_metrics`
- `latest_hit_rate_avg`：TopK 命中“该族最新文档”的比例，函数：`_quality_metrics`
- `precision_at_k_proxy_avg`：基于 `expected_keywords` 的代理 Precision@K，函数：`_quality_metrics`

3. B 组关键步骤
- 关键词过滤：`_keyword_filter`
- 近似家族归并：`_family_key`
- 新鲜度加权与去重：`_dedup_and_freshness`

## 5. 判定标准（建议）

1. 若 B 组满足：
- P95 不劣于 A 超过 5%
- Precision@5 提升 >= 8%
- LatestHit@5 提升 >= 15%
则可灰度上线。

2. 若 B 组 P95 上升 > 10%：
- 改为“仅强关键词触发关键词层”
- 强关键词可按规则：告警码、系统名、错误码、英文大写+数字混合词。

## 6. 注意事项（不确定项）

1. `precision_at_k_proxy` 是代理指标，不等同人工标注 Precision@K。
- 原因：当前仓库未提供全量人工标注评测集。
- 若要严格评估，需新增带金标答案/证据的数据集。

2. 若开启 `--use-rewrite`，会引入模型调用波动。
- 相关函数：`src/hz_bank_rag/retrieval/query_rewrite.py::QueryRewriter.rewrite`
- 建议先测 `rewrite=off` 的纯检索/重排性能，再测 `rewrite=on` 的端到端性能。
