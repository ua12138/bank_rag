# RAG_PLUS 技术架构说明（按调用顺序）

## 1. 目标
在主 RAG 能力上增加：鉴权、限流、并发保护、智能路由、工具注册、工作流。

## 2. /plus/query 执行顺序
1. token 校验
2. scope 校验
3. 用户限流
4. 本地并发舱壁
5. Redis 分布式并发槽位
6. 智能路由
7. 查询缓存
8. QA 执行
9. 回写缓存

## 3. 核心模块
- `auth.py`：登录与 token
- `redis_runtime.py`：缓存、限流、并发槽位
- `router.py`：问题复杂度路由
- `workflow.py`：混合意图工作流

## 4. 规划项
- `/plus/query` 透传 `enable_kg`、`kg_hop_limit`
- `/plus/query` 返回 `stage_metrics`、`token_usage`、`kg_citations`
- 不确定：`RAG_PLUS/schemas.py::PlusQueryRequest` 当前未包含这些字段
