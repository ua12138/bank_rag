# ACCEPTANCE（中文验收说明）

## 1. 验收目标

覆盖：API、入库、查询、bad-case、ragas、collection 管理、MCP 封装服务、一键回归。

## 2. 环境准备

```powershell
cd D:\code_warehouse\codex_learn\hz_bank_rag
pip install -e .
pip install -e .[ragas]

$env:HZ_RAG_SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
$env:HZ_RAG_SILICONFLOW_API_KEY="<你的 key>"
$env:HZ_RAG_USE_MILVUS="true"
$env:HZ_RAG_MILVUS_URI="http://47.111.101.201:19530"
```

## 3. API 服务验收

1. 启动 API：
```powershell
uvicorn hz_bank_rag.api.main:app --reload --port 8090
```
2. `GET /health` 期望 200
3. `POST /demo/seed` 期望 `count >= 1`
4. `POST /query` 期望返回 `answer` 与 `citations`

## 4. 入库版本化与去重验收（新增）

目标：验证 `content_hash` 幂等、`doc_family_id/version_no/is_active`、近重复检测链路。

1. 准备同族文件
- `ops_manual_v1.md`
- `ops_manual_v2.md`（内容有增量）
- `ops_manual_copy.md`（与 v2 完全相同）

2. 依次调用入库接口
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/knowledge-bases/hz-bank-demo/documents" -ContentType "application/json" -Body '{"file_path":"D:\\code_warehouse\\codex_learn\\hz_bank_rag\\data\\demo_kb\\ops_manual_v1.md"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/knowledge-bases/hz-bank-demo/documents" -ContentType "application/json" -Body '{"file_path":"D:\\code_warehouse\\codex_learn\\hz_bank_rag\\data\\demo_kb\\ops_manual_v2.md"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/knowledge-bases/hz-bank-demo/documents" -ContentType "application/json" -Body '{"file_path":"D:\\code_warehouse\\codex_learn\\hz_bank_rag\\data\\demo_kb\\ops_manual_copy.md"}'
```

3. 期望结果
- 第 1 次：`status=ingested`，`version_no=1`，`is_active=true`
- 第 2 次：`status=ingested`，`version_no=2`，同 `doc_family_id`，v1 自动 `is_active=false`
- 第 3 次：`status=duplicate_exact`，`idempotent=true`，不重复切块与向量化

4. 验证接口
- `GET /knowledge-bases/documents?kb_id=hz-bank-demo&limit=20`
- 期望能看到 `doc_family_id/version_no/effective_at/is_active/content_hash/near_hash/keywords`

5. 不达预期排查
- 若没有版本字段：确认已重启 API（加载新 schema）
- 若重复未幂等：检查 `content_hash` 是否为空（看 documents 列表）
- 若 `is_active` 都是 true：检查同族命名是否命中（文件名需同族可归并）

## 5. 检索策略参数验收（新增）

目标：验证 `retrieval_scope`、`freshness_weight`、`dedup_by_family` 行为。

1. `active_only`（默认线上模式）
```json
{
  "kb_id": "hz-bank-demo",
  "query": "连接池告警处理步骤",
  "retrieval_scope": "active_only",
  "dedup_by_family": true,
  "freshness_weight": 0.08,
  "top_k": 5
}
```
期望：
- `citations` 中同 `doc_family_id` 默认仅保留 1 条
- 优先返回最新版本（`effective_at` 新）

2. `include_history`（历史回溯模式）
```json
{
  "kb_id": "hz-bank-demo",
  "query": "连接池告警处理步骤",
  "retrieval_scope": "include_history",
  "dedup_by_family": false,
  "freshness_weight": 0.0,
  "top_k": 10
}
```
期望：
- 同族可返回多版本结果
- `citations` 可见历史版本文档

3. 强关键词约束验证
```json
{
  "kb_id": "hz-bank-demo",
  "query": "DB_CONN_104 告警怎么处理",
  "retrieval_scope": "active_only",
  "dedup_by_family": true
}
```
期望：
- 候选更聚焦含 `DB_CONN_104` 或相关强词的片段
- 无强词时会回退到原候选，避免召回为空

4. 不达预期排查
- 若 `retrieval_scope` 无效：确认请求体字段名拼写正确
- 若新鲜度无明显变化：检查文档 `effective_at` 是否有差异
- 若去重未生效：检查 chunk 元数据是否包含 `doc_family_id`

## 6. bad-case 与评估验收

1. `POST /bad-cases`
2. `GET /bad-cases`
3. `GET /bad-cases/ragas-dataset`
4. `POST /evaluate/ragas`
5. `POST /evaluate/ragas/official`
6. `POST /evaluate/ragas/ab`

期望：
- A/B 接口返回轻量/官方结果和 delta。

## 7. Collection 策略验收

1. `GET /collections/policy`
2. `GET /collections/managed`
3. `POST /collections/cleanup?dry_run=true`

期望：
- 命名规则可见
- managed/stale 集合可见
- dry-run 不删除数据

## 8. MCP 封装服务验收

1. 启动 MCP：
```powershell
.\scripts\start_mcp.ps1 -Port 8091
```
2. `GET /health`（MCP 服务）
3. `GET /tools`，期望含 `rag.query` 等工具
4. `POST /mcp` 调用 `initialize`
5. `POST /mcp` 调用 `tools/list`
6. `POST /mcp` 调用 `tools/call`（例如 `rag.health`）

期望：
- JSON-RPC 返回 `result`
- 工具调用可返回结构化内容

## 9. 一键回归验收

执行：
```powershell
.\scripts\regression_run.ps1 -KbId hz-bank-demo
```

期望：
- 生成 `reports/regression_report_*.json` 和 `*.md`
- 报告包含每一步 pass/fail

## 10. 测试验收

执行：
```powershell
pytest -q --basetemp .pytest_tmp
```

说明：
- 若出现 `.pytest_tmp` ACL 拒绝访问，这是系统权限问题，不是业务功能错误。

## 11. 不达预期排查

1. 缺 API Key：模型调用失败
2. 缺 ragas 依赖：官方评估失败
3. Milvus 不通：检索退化或连接报错
4. ACL 拒绝访问：影响 pytest 临时目录，不影响 API/MCP 主流程
5. Swagger 与 YAML 不一致：以 `spec/openapi.yaml` 与 `/docs` 双对照，确认请求字段为 `retrieval_scope/freshness_weight/dedup_by_family`
