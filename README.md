# 银行生产运行中心 RAG 项目（操作手册）

本文档面向“直接上手运行”的场景，默认环境为 Windows + PowerShell。

## 一、目录结构说明

- `src/`：核心源码（API、检索、入库、存储、评估、MCP）
- `spec/`：规范文档与接口说明
- `data/demo_kb/`：入库数据目录（会被 `/demo/seed` 扫描）
- `data/eval_samples/`：评估样例目录（不会入库）
- `tests/`：自动化测试
- `scripts/`：运维/回归脚本
  - `regression_run.ps1`：一键回归入口
  - `regression_run.py`：回归执行与报告生成
  - `perf_ab_eval.ps1`：A/B 性能评估入口（关键词层 + 近似文件打分）
  - `perf_ab_eval.py`：A/B 性能评估执行与报告生成
  - `start_mcp.ps1`：启动 MCP 封装服务
- `reports/`：回归报告输出目录
- `docs/`：过程文档（项目总结、面试题库、会话状态）
  - `docs/INDEX.md`：文档统一入口与去重导航
- `.agents/`：技能配置目录

临时目录：
- `.pytest_tmp/` 与 `data/pytest_tmp/` 为 pytest 临时目录，不是业务目录。
- 当前机器存在 ACL 拒绝访问时可先忽略，不影响 API 与 MCP 服务运行。

## 二、环境准备

```powershell
cd D:\code_warehouse\codex_learn\hz_bank_rag
pip install -e .
# 如需官方 ragas pipeline
pip install -e .[ragas]

$env:HZ_RAG_SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
$env:HZ_RAG_SILICONFLOW_API_KEY="<你的 key>"
$env:HZ_RAG_USE_MILVUS="true"
$env:HZ_RAG_MILVUS_URI="http://47.111.101.201:19530"
```

Milvus 版本说明（当前项目真实环境）：
- Milvus Server：`2.6.9`
- Python 客户端（pymilvus）：`2.6.11`（已在 `pyproject.toml` 锁定）

## 三、启动 HTTP API

```powershell
uvicorn hz_bank_rag.api.main:app --reload --port 8090
```

Swagger：`http://127.0.0.1:8090/docs`

## 四、启动 MCP 封装服务（供 Agent 调用）

方式 1（推荐）：
```powershell
.\scripts\start_mcp.ps1 -Port 8091
```

方式 2（命令行入口）：
```powershell
hz-rag-mcp
```

MCP 服务地址：`http://127.0.0.1:8091`

可用端点：
- `GET /health`
- `GET /tools`
- `POST /tools/call`
- `POST /mcp`（JSON-RPC，支持 `initialize`、`tools/list`、`tools/call`）

## 五、快速跑通流程

1. `POST /demo/seed`：导入 `data/demo_kb/` 文档
2. `POST /query`：发起问答
3. `POST /bad-cases`：提交 bad-case
4. `GET /bad-cases/ragas-dataset`：生成评估数据
5. `POST /evaluate/ragas`：轻量评估
6. `POST /evaluate/ragas/official`：官方评估
7. `POST /evaluate/ragas/ab`：A/B 对照

`POST /query` 新增可选参数（入库与召回优化版）：
- `retrieval_scope`：`active_only | include_history`
- `freshness_weight`：新鲜度权重（默认 `0.08`）
- `dedup_by_family`：是否按文档族去重（默认 `true`）

默认线上策略：
- `retrieval_scope=active_only`
- `dedup_by_family=true`
- `freshness_weight>0`

## 六、PDF 图文同页解析说明

- 当前 PDF 解析为“同页双通道”：
  - 提取该页正文文本（`[pdf-page-N-text]`）
  - 同时提取该页图片 OCR（`[pdf-page-N-image-M-ocr]`）
- 这样可以避免“有正文就跳过图片”的信息丢失问题。
- 下游切块时会保留这些页号和图片序号标记，便于检索和答案归因。

## 七、重复入库校验说明

系统已默认开启“禁止重复入库”：

1. `exact duplicate`：同 `content_hash`，直接幂等返回（`status=duplicate_exact`），不重复切块/向量化。
2. `near duplicate`：基于 SimHash + 汉明距离检测（默认阈值 `3`），可配置仅标记或拒绝。
3. `same family update`：同文档族生成新版本，旧版本自动 `inactive`，新版本 `active`。

关键元数据字段（SQLite `documents`）：
- `doc_family_id`
- `version_no`
- `effective_at`
- `is_active`
- `content_hash`
- `near_hash`
- `keywords_json`

## 八、一键回归

```powershell
.\scripts\regression_run.ps1 -KbId hz-bank-demo
```

输出报告：
- `reports/regression_report_*.json`
- `reports/regression_report_*.md`

说明：
- 未配置 API Key 时，仍会生成报告，但状态通常为 `partial`。

## 九、A/B 性能评估（中等并发口径）

目标：
- 评估“关键词层 + 近似文件打分（同族去重 + 最新优先）”相对基线的收益。

命令：

```powershell
.\scripts\perf_ab_eval.ps1 -KbId hz-bank-demo -Concurrency 20 -Rounds 3
```

输出：
- `reports/perf_ab_report_*.json`
- `reports/perf_ab_report_*.md`

样例查询集：
- `data/eval_samples/perf_queries.json`

指标：
- 性能：P50/P95/P99、QPS
- 质量：重复证据率、最新文档命中率、Precision@K 代理指标

详细说明：
- `docs/code_reading/PERF_AB_EVAL.md`

## 十、Collection 命名与清理

命名规则：
- `<base>__<embedding_model_slug>__d<dim>__hbm25`

BM25 持久化策略：
- 默认优先使用 Milvus 稀疏检索（`SPARSE_FLOAT_VECTOR + BM25 Function`）实现持久化 BM25。
- 若 Milvus 稀疏能力不可用，会自动降级到进程内 BM25（仅兜底，不建议生产长期使用）。
- 若检测到历史 dense-only collection（旧命名），系统会自动迁移到 `__hbm25` 新 collection（仅首次）。

相关接口：
- `GET /collections/policy`
- `GET /collections/managed`
- `POST /collections/cleanup?dry_run=true`
- `POST /collections/cleanup?dry_run=false`

## 十一、测试

```powershell
pytest -q
```

新增覆盖点：
- `QAService`：缓存命中、会话压缩
- `seed_demo`：评估样例排除规则
- `MetadataStore`：bad-case 到 ragas 映射、会话清理
- `MCP wrapper`：工具列表与 JSON-RPC 基础调用

## 十二、当前已知问题

- `.pytest_tmp` 与 `data/pytest_tmp` 目录在你当前机器上可能有 ACL 拒绝访问。
- 该问题属于系统权限，不是业务代码问题；不影响 API 与 MCP 服务正常运行。

## 十三、RAG_PLUS（增强版）说明

`RAG_PLUS/` 是独立增强目录，包含：

- 高并发可用性：本地舱壁 + Redis 分布式并发槽位 + 用户限流
- 智能路由：按问题复杂度分配小模型/大模型/风险模型
- 企业级 MCP 注册中心：工具注册、检索、scope 鉴权
- 混合意图工作流：检索问答 + 工具推荐 + 报告聚合
- 鉴权：Bearer Token（HMAC 签名）+ 细粒度 scope
- Redis 负载优化：缓存、轮询负载、分布式回压

详细架构见：`spec/RAG_PLUS_SPEC.md`

## 十四、RAG_PLUS 启动步骤（详细）

### 12.1 安装依赖

```powershell
cd D:\code_warehouse\codex_learn\hz_bank_rag
pip install -e .
# 建议安装 redis 客户端以启用分布式缓存和并发槽位
pip install redis
```

### 12.2 设置环境变量（最小集）

```powershell
$env:HZ_RAG_SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
$env:HZ_RAG_SILICONFLOW_API_KEY="<你的key>"
$env:HZ_RAG_USE_MILVUS="true"
$env:HZ_RAG_MILVUS_URI="http://47.111.101.201:19530"

# RAG_PLUS
$env:HZ_RAG_PLUS_AUTH_SECRET="please-change-this-secret"
$env:HZ_RAG_PLUS_ADMIN_USERNAME="admin"
$env:HZ_RAG_PLUS_ADMIN_PASSWORD="admin123"
$env:HZ_RAG_PLUS_REDIS_ENABLED="true"
$env:HZ_RAG_PLUS_REDIS_URL="redis://127.0.0.1:6379/0"
```

### 12.3 启动服务

方式 1（脚本）：
```powershell
.\scripts\start_rag_plus.ps1 -Port 8092
```

方式 2（命令）：
```powershell
uvicorn RAG_PLUS.main:app --reload --port 8092
```

方式 3（安装后脚本）：
```powershell
hz-rag-plus
```

Swagger：`http://127.0.0.1:8092/docs`

## 十五、RAG_PLUS 接口实操

### 13.1 获取 Token

接口：`POST /plus/auth/token`

请求体：
```json
{
  "username": "admin",
  "password": "admin123"
}
```

PowerShell 示例：
```powershell
$tokenResp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8092/plus/auth/token" -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'
$token = $tokenResp.access_token
```

### 13.2 导入 demo 数据

接口：`POST /plus/demo/seed`（需要 `rag:admin`）

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8092/plus/demo/seed" -Headers @{ Authorization = "Bearer $token" }
```

### 13.3 智能路由问答

接口：`POST /plus/query`

请求体：
```json
{
  "kb_id": "hz-bank-demo",
  "query": "请分析网银交易超时的可能根因并给出排障步骤",
  "session_id": "s001",
  "use_memory": true,
  "top_k": 5,
  "candidate_multiplier": 4
}
```

返回中重点关注：
- `route.level`：simple/standard/complex/risky
- `route.selected_model`：实际选择模型
- `cache_hit`：是否命中缓存
- `citations`：证据片段

### 13.4 MCP 工具注册

接口：`POST /plus/mcp/tools/register`

```json
{
  "tool_id": "ticket.search",
  "name": "工单查询",
  "description": "按系统、时间范围查询历史工单",
  "endpoint": "http://ticket-service/api/search",
  "method": "POST",
  "tags": ["工单", "运维", "查询"],
  "scopes": ["tools:read"],
  "input_schema": {
    "type": "object",
    "properties": {
      "system": {"type": "string"},
      "start_time": {"type": "string"},
      "end_time": {"type": "string"}
    }
  }
}
```

### 13.5 MCP 工具搜索

接口：`POST /plus/mcp/tools/search`

```json
{
  "query": "查交易系统近7天工单",
  "required_tags": ["工单"],
  "limit": 5
}
```

### 13.6 混合意图工作流

接口：`POST /plus/workflow/run`

请求体：
```json
{
  "kb_id": "hz-bank-demo",
  "query": "先分析交易超时原因，再推荐能查工单的工具，最后输出处理报告",
  "session_id": "wf-001",
  "top_k": 5,
  "candidate_multiplier": 4
}
```

返回字段：
- `intents`：识别到的意图集合
- `plan`：拆解后的执行计划
- `qa`：RAG 问答结果
- `tools`：匹配到的工具
- `report`：聚合报告

## 十六、RAG_PLUS 常见问题排查

1. `/plus/auth/token` 返回 401
- 检查 `HZ_RAG_PLUS_ADMIN_USERNAME/HZ_RAG_PLUS_ADMIN_PASSWORD` 是否与请求一致。

2. `/plus/query` 返回 429
- 触发了限流或并发槽位上限。
- 调高 `HZ_RAG_PLUS_RATE_LIMIT_PER_USER_PER_MINUTE`、`HZ_RAG_PLUS_MAX_INFLIGHT_GLOBAL`、`HZ_RAG_PLUS_MAX_INFLIGHT_PER_KB`。

3. Redis 未生效
- 看 `/plus/health` 的 `redis_enabled` 是否为 `true`。
- 检查 Redis 地址与网络连通性。

4. 工具搜索为空
- 检查工具是否已注册。
- 检查 token scope 是否覆盖工具要求的 scopes。
