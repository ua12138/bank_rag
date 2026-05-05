# RAG_PLUS 技术架构说明（增强版）

## 1. 目标与范围

`RAG_PLUS` 是在现有 `hz_bank_rag` 基础上的增强实现，专门解决以下工程问题：

1. 资源有限时的高并发可用性（数百并发问答）
2. 基于 Prompt 复杂度的智能模型路由
3. 企业级 MCP 工具注册、发现与鉴权
4. 混合意图（检索 + 工具 + 报告 +行动建议）工作流
5. 鉴权与权限控制
6. Redis 缓存 + 分布式并发槽位 + 轮询负载优化

新增代码全部位于 `RAG_PLUS/` 目录，与原有 `src/hz_bank_rag/` 主链路隔离。

## 2. 目录结构

- `RAG_PLUS/config.py`：增强配置与环境变量
- `RAG_PLUS/auth.py`：Token 签发与鉴权校验（scope 控制）
- `RAG_PLUS/redis_runtime.py`：Redis 缓存、限流、并发槽位、轮询
- `RAG_PLUS/router.py`：智能路由器（简单/标准/复杂/高风险）
- `RAG_PLUS/mcp_registry.py`：MCP 工具注册中心
- `RAG_PLUS/workflow.py`：混合意图流程引擎
- `RAG_PLUS/rag_runtime.py`：复用原 RAG 组件并支持按路由选模型
- `RAG_PLUS/main.py`：FastAPI 入口

## 3. 架构总览

请求链路如下：

1. 用户调用 `/plus/query`
2. 鉴权校验（Bearer Token + scope）
3. 用户限流（Redis INCR + 窗口）
4. 并发控制（本地 Semaphore + Redis 分布式槽位）
5. 智能路由（选择模型池与是否 rerank）
6. 查询缓存命中（Redis / 本地降级）
7. 检索与回答（复用 `hz_bank_rag` 检索与记忆能力）
8. 回写缓存并返回

## 4. 高并发可用性设计

### 4.1 多层回压

- 本地舱壁：`LocalConcurrencyGuard`（`BoundedSemaphore`）
- 分布式槽位：`RedisRuntime.acquire_slot()`，按
  - 全局桶 `global`
  - 知识库桶 `kb:<kb_id>`

超过阈值直接返回 `429`，避免实例雪崩与依赖过载。

### 4.2 限流

- 用户维度限流：`rate_limit_per_user_per_minute`
- Redis 计数不可用时降级本地窗口计数

### 4.3 缓存

- Query 级缓存键包含：`kb_id + query_hash + top_k + multiplier + selected_model + session_id + use_memory`
- TTL 可配置，降低高频重复问题负载

## 5. 智能路由设计

`SmartModelRouter` 通过以下信号估算复杂度：

- 文本长度
- 复杂关键词（如“架构”“根因”“对比”“多轮”等）
- 句法复杂度（分句数量）
- 高风险词（如“删库”“紧急变更”“回滚”等）

输出：

- `level`: simple / standard / complex / risky
- `selected_model`: 从对应模型池轮询选取
- `use_rerank`: 是否启用重排

模型池默认配置：

- `small_model_pool`: 小模型低成本
- `large_model_pool`: 大模型高质量
- `risky_model_pool`: 高风险问题专用

## 6. MCP 注册中心与鉴权

### 6.1 工具注册

通过 `/plus/mcp/tools/register` 提交工具元数据：

- `tool_id/name/description/endpoint/method`
- `tags/scopes/owner`
- `input_schema/health_score/avg_latency_ms`

### 6.2 工具发现

`/plus/mcp/tools/search` 采用混合排序：

1. Query 与工具名称/描述/标签匹配得分
2. 工具健康度加分
3. 工具时延惩罚（低时延优先）

### 6.3 权限控制

- Token 内含 `scopes`
- 工具声明 `required scopes`
- 搜索与调用前进行 scope 比对，未授权工具不可见

## 7. 混合意图工作流

`MixedIntentWorkflowEngine`：

1. `detect_intents`：识别 `qa/tool_lookup/report/action_plan`
2. `build_plan`：构建 DAG 步骤
3. `run`：执行 QA、工具推荐、行动计划生成、报告聚合

适合问题示例：

- “帮我查故障原因，并推荐可调用的工单工具，最后给个处置报告”

## 8. 鉴权设计

`RAG_PLUS/auth.py` 使用 HMAC 签名 Token（JWT 形态）：

- 登录接口：`/plus/auth/token`
- 内含字段：`sub/roles/scopes/iat/exp`
- 校验：签名 + 过期时间 + scope

说明：
- 该实现用于项目内自包含演示。
- 生产建议替换为企业 OIDC/LDAP/IAM。

## 9. Redis 负载优化策略

`RedisRuntime` 支持：

- `get_json/set_json`：查询缓存
- `allow_rate`：限流窗口计数
- `acquire_slot/release_slot`：分布式并发槽位
- `select_from_pool`：模型池轮询负载均衡

Redis 不可用时自动降级本地内存，不阻断服务。

## 10. RAG_PLUS API 清单

- `GET /plus/health`
- `POST /plus/auth/token`
- `POST /plus/query`
- `POST /plus/mcp/tools/register`
- `GET /plus/mcp/tools`
- `POST /plus/mcp/tools/search`
- `POST /plus/workflow/run`
- `POST /plus/demo/seed`
- `GET /plus/mcp/snapshot`

## 11. 关键配置项（环境变量前缀 `HZ_RAG_PLUS_`）

- `AUTH_SECRET`
- `AUTH_TOKEN_TTL_SECONDS`
- `REDIS_ENABLED`
- `REDIS_URL`
- `MAX_INFLIGHT_GLOBAL`
- `MAX_INFLIGHT_PER_KB`
- `RATE_LIMIT_PER_USER_PER_MINUTE`
- `SMALL_MODEL_POOL`
- `LARGE_MODEL_POOL`
- `RISKY_MODEL_POOL`

## 12. 与主项目关系

- 复用：向量库（稠密+Milvus 稀疏 BM25）、检索、重写、重排、会话记忆、seed 数据
- 复用入库去重：同 `kb_id` 下按 `file_path` + 文件 `SHA256` 禁止重复入库
- 隔离：增强功能全部在 `RAG_PLUS/`，避免影响原有 API
- 启动互不冲突：主项目默认 8090；RAG_PLUS 建议 8092
- Milvus 版本基线：
  - Server：`2.6.9`
  - `pymilvus`：`2.6.11`
