# 银行生产运行中心 RAG 项目（操作手册）

本文档按“先启动、再调用、再排障、最后看扩展”的顺序组织。

## 1. 项目结构
- `src/`：主服务代码
- `RAG_PLUS/`：增强服务代码
- `spec/`：接口契约与技术规格
- `docs/`：代码走读与学习资料
- `scripts/`：启动、回归、A/B 评估脚本

## 2. 环境准备
```powershell
cd D:\code_warehouse\codex_learn\hz_bank_rag
pip install -e .
pip install -e .[ragas]
```

```powershell
$env:HZ_RAG_SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1"
$env:HZ_RAG_SILICONFLOW_API_KEY="<你的key>"
$env:HZ_RAG_USE_MILVUS="true"
$env:HZ_RAG_MILVUS_URI="http://47.111.101.201:19530"
```

## 3. 启动主服务
```powershell
uvicorn hz_bank_rag.api.main:app --reload --port 8090
```
- Swagger: `http://127.0.0.1:8090/docs`
- 健康检查: `GET /health`

## 4. 启动 MCP 服务
```powershell
.\scripts\start_mcp.ps1 -Port 8091
```
或
```powershell
hz-rag-mcp
```

## 5. 最小跑通顺序
1. `POST /demo/seed`
2. `POST /query`
3. `POST /bad-cases`
4. `GET /bad-cases/ragas-dataset`
5. `POST /evaluate/ragas`
6. `POST /evaluate/ragas/official`
7. `POST /evaluate/ragas/ab`

## 6. 查询参数与默认策略
- `retrieval_scope`: `active_only | include_history`
- `freshness_weight`: 默认 `0.08`
- `dedup_by_family`: 默认 `true`

## 7. 入库与查询链路
- 入库入口：`src/hz_bank_rag/storage/rag_repository.py::ingest_document`
- 查询入口：`src/hz_bank_rag/api/main.py::query`
- 编排核心：`src/hz_bank_rag/service/qa_service.py::ask`

## 8. 缓存与性能
- L1: `EmbeddingCache`
- L2: `RetrievalCache`
- L3: `AnswerCache`
- 文档变更后按 `kb_id` 失效 L2/L3

```powershell
.\scripts\perf_ab_eval.ps1 -KbId hz-bank-demo -Concurrency 20 -Rounds 3
```

## 9. 回归与测试
```powershell
.\scripts\regression_run.ps1 -KbId hz-bank-demo
pytest -q
```

## 10. RAG_PLUS 操作顺序
1. 获取 token: `POST /plus/auth/token`
2. 导入演示数据: `POST /plus/demo/seed`
3. 问答: `POST /plus/query`
4. 工具注册（可选）: `POST /plus/mcp/tools/register`
5. 工具检索（可选）: `POST /plus/mcp/tools/search`
6. 工作流（可选）: `POST /plus/workflow/run`

## 11. 本期规划项（未完整落地）
### 11.1 KG 能力（规划）
- 规划接口：`/kg/rebuild`、`/kg/entities/search`、`/kg/subgraph`、`/kg/path`
- 规划字段：`enable_kg`、`kg_hop_limit`、`kg_citations`

### 11.2 耗时与 Token 统计（规划）
- 固定口径：`rewrite_ms / retrieval_ms / rerank_ms / llm_ms / total_ms`
- token 来源优先级：`API usage -> 本地估算`
- 规划接口：`/metrics/overview`、`/metrics/tokens`、`/metrics/latency/stages`、`/metrics/requests`

### 11.3 前端页面（规划）
- `/ui/kg`、`/ui/metrics`

## 12. 文档导航
- `spec/DEV_SPEC.md`
- `spec/openapi.yaml`
- `spec/RAG_PLUS_SPEC.md`
- `docs/code_reading/REQUEST_FLOW.md`
- `docs/code_reading/PROJECT_MAP.md`
- `docs/learning/03_REQUEST_CALL_CHAIN.md`
