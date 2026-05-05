# STARTUP_FLOW（函数级调用链版）

## 1. 启动命令与入口绑定

| 启动命令 | 入口模块 | 模块级对象 | 实际构造函数 |
|---|---|---|---|
| `uvicorn hz_bank_rag.api.main:app --reload --port 8090` | `src/hz_bank_rag/api/main.py` | `app = build_app()` | `build_app()` |
| `uvicorn hz_bank_rag.mcp.main:app --host 127.0.0.1 --port 8091 --reload` | `src/hz_bank_rag/mcp/main.py` | `app = build_mcp_app()` | `build_mcp_app()` |
| `uvicorn RAG_PLUS.main:app --host 0.0.0.0 --port 8092 --reload` | `RAG_PLUS/main.py` | `app = build_app()` | `build_app()` |

---

## 2. 主 API 启动调用栈（`src/hz_bank_rag/api/main.py`）

### Step A1
- 文件路径：`src/hz_bank_rag/api/main.py`
- 类/函数：`build_app() -> FastAPI`
- 上游调用者：`uvicorn` 导入模块时读取 `app`
- 下游被调用函数：`MetadataStore(...)`, `BM25Store()`, `MilvusVectorStore(...)|InMemoryVectorStore(...)`, `RAGRepository(...)`, `HybridRetriever(...)`, `QAService(...)`, `RagasRunner()`
- 核心入参：无显式参数，读取 `settings`
- 核心出参/副作用：返回 `FastAPI` 应用，组件实例驻留闭包

### Step A2（配置加载）
- 文件路径：`src/hz_bank_rag/core/config.py`
- 类/函数：`Settings(BaseSettings)`, `settings = Settings()`
- 上游调用者：`api/main.py` import `settings`
- 下游被调用函数：Pydantic BaseSettings 解析环境变量
- 核心入参：环境变量前缀 `HZ_RAG_*`
- 核心出参/副作用：配置对象供 `build_app()` 实例化依赖

### Step A3（路由注册到函数级）
- 文件路径：`src/hz_bank_rag/api/main.py`
- 类/函数：
  - `query(req: QueryRequest)` -> `qa_service.ask(...)`
  - `query_stream(req: QueryRequest)` -> `qa_service.ask_stream(...)`
  - `ingest_document(...)` -> `repo.ingest_document(...)`
  - `evaluate_ragas_ab(req: EvalRequest)` -> `ragas_runner.evaluate_ab(...)`
  - `bad_case(req: BadCaseRequest)` -> `qa_service.record_bad_case(...)`
- 上游调用者：FastAPI 路由分发器
- 下游被调用函数：`QAService` / `RAGRepository` / `RagasRunner`
- 核心入参：Pydantic 请求模型
- 核心出参/副作用：HTTP JSON 响应；异常被映射为 `HTTPException`

### Step A4（启动完成状态）
- 文件路径：`src/hz_bank_rag/api/main.py`
- 类/函数：`health()`
- 上游调用者：`GET /health`
- 下游被调用函数：读取 `settings`、`vector_store.available`
- 核心入参：无
- 核心出参：`status/use_milvus/milvus_available/model 配置/cache 配置`

---

## 3. MCP 启动调用栈（`src/hz_bank_rag/mcp/main.py`）

### Step M1
- 文件路径：`src/hz_bank_rag/mcp/main.py`
- 类/函数：`build_mcp_app() -> FastAPI`
- 上游调用者：`uvicorn` 导入模块时读取 `app`
- 下游被调用函数：`build_runtime()`（来自 `src/hz_bank_rag/mcp/runtime.py`）
- 核心入参：无
- 核心出参/副作用：`runtime`（含 `repo/qa/ragas/vector_store`）绑定到路由闭包

### Step M2（runtime 组装）
- 文件路径：`src/hz_bank_rag/mcp/runtime.py`
- 类/函数：`build_runtime() -> Runtime`
- 上游调用者：`build_mcp_app`
- 下游被调用函数：`MetadataStore`, `BM25Store`, `MilvusVectorStore|InMemoryVectorStore`, `RAGRepository`, `HybridRetriever`, `QAService`, `RagasRunner`
- 核心入参：无（内部读取 `settings`）
- 核心出参：`Runtime(meta, repo, qa, ragas, vector_store)`

### Step M3（工具注册与分发）
- 文件路径：`src/hz_bank_rag/mcp/main.py`
- 类/函数：`_tool_specs()`, `_call_tool(runtime, name, arguments)`, `mcp_rpc(req)`
- 上游调用者：`POST /tools/call` 或 `POST /mcp` 的 `tools/call`
- 下游被调用函数：
  - `runtime.qa.ask`
  - `runtime.repo.list_documents`
  - `runtime.qa.record_bad_case`
  - `runtime.ragas.evaluate_ab`
- 核心入参：`name: str`, `arguments: dict`
- 核心出参：`dict`（工具结果）或 JSON-RPC `error`

### Step M4（启动完成状态）
- 文件路径：`src/hz_bank_rag/mcp/main.py`
- 类/函数：`health()`
- 上游调用者：`GET /health`
- 核心出参：`service/tools/siliconflow_key_configured`

---

## 4. RAG_PLUS 启动调用栈（`RAG_PLUS/main.py`）

### Step P1
- 文件路径：`RAG_PLUS/main.py`
- 类/函数：`build_app() -> FastAPI`
- 上游调用者：`uvicorn` 导入模块时读取 `app`
- 下游被调用函数：`build_runtime`, `AdaptiveQAExecutor`, `RedisRuntime`, `AuthService`, `SmartModelRouter`, `MCPRegistry`, `MixedIntentWorkflowEngine`, `LocalConcurrencyGuard`
- 核心入参：无（读取 `plus_settings`）
- 核心出参/副作用：增强版应用对象与所有中间件能力闭包化

### Step P2（基础 RAG runtime 复用）
- 文件路径：`RAG_PLUS/rag_runtime.py`
- 类/函数：`build_runtime() -> RagRuntime`
- 上游调用者：`RAG_PLUS/main.py::build_app`
- 下游被调用函数：`MetadataStore`, `BM25Store`, `MilvusVectorStore|InMemoryVectorStore`, `RAGRepository`, `HybridRetriever`, `QAService`, `SiliconFlowClient`
- 核心入参：无（读取 `base_settings`）
- 核心出参：`RagRuntime(meta, repo, qa, llm)`

### Step P3（路由注册到函数级）
- 文件路径：`RAG_PLUS/main.py`
- 类/函数：
  - `issue_token(req)` -> `auth_service.login`
  - `plus_query(req, claims, request)` -> `router.route` + `adaptive_qa.ask` + `redis_runtime.get_json/set_json`
  - `register_tool(req, claims)` -> `registry.register`
  - `search_tools(req, claims)` -> `registry.search`
  - `run_workflow(req, claims)` -> `workflow_engine.run`
- 上游调用者：FastAPI 路由分发器
- 下游被调用函数：鉴权、限流、缓存、路由、工具注册与工作流引擎
- 核心入参：`PlusQueryRequest/TokenRequest/ToolRegistrationRequest/WorkflowRunRequest`
- 核心出参/副作用：JSON 响应；Redis 计数、缓存读写、并发槽位 acquire/release

### Step P4（启动完成状态）
- 文件路径：`RAG_PLUS/main.py`
- 类/函数：`health()`
- 上游调用者：`GET /plus/health`
- 核心出参：`redis_enabled/model_pools/limits`

---

## 5. 启动链路 ASCII（函数节点）

### 主 API
```text
uvicorn hz_bank_rag.api.main:app
  -> import src/hz_bank_rag/api/main.py
  -> app = build_app()
     -> MetadataStore.__init__
     -> BM25Store.__init__
     -> MilvusVectorStore.__init__ | InMemoryVectorStore.__init__
     -> RAGRepository.__init__
     -> HybridRetriever.__init__
     -> QAService.__init__
     -> RagasRunner.__init__
     -> register route: query() -> QAService.ask()
     -> register route: ingest_document() -> RAGRepository.ingest_document()
     -> register route: evaluate_ragas_ab() -> RagasRunner.evaluate_ab()
  -> server ready
```

### MCP
```text
uvicorn hz_bank_rag.mcp.main:app
  -> import src/hz_bank_rag/mcp/main.py
  -> app = build_mcp_app()
     -> build_runtime()
        -> MetadataStore/BM25Store/MilvusVectorStore/RAGRepository/HybridRetriever/QAService/RagasRunner
     -> register route: /tools/call -> _call_tool()
     -> register route: /mcp -> mcp_rpc()
        -> tools/call -> _call_tool() -> runtime.qa.ask | runtime.ragas.evaluate_ab ...
  -> server ready
```

### RAG_PLUS
```text
uvicorn RAG_PLUS.main:app
  -> import RAG_PLUS/main.py
  -> app = build_app()
     -> build_runtime() -> RagRuntime
     -> AdaptiveQAExecutor.__init__
     -> RedisRuntime.__init__
     -> AuthService.__init__
     -> SmartModelRouter.__init__
     -> MCPRegistry.__init__
     -> MixedIntentWorkflowEngine.__init__
     -> register route: plus_query() -> router.route() -> adaptive_qa.ask()
  -> server ready
```

---

## 6. 不确定项与验证命令
- 不确定：线上是否分进程部署三套服务，或仅暴露其中一种入口。
- 验证命令：
```powershell
Get-NetTCPConnection -LocalPort 8090,8091,8092 -State Listen
Invoke-RestMethod http://127.0.0.1:8090/health
Invoke-RestMethod http://127.0.0.1:8091/health
Invoke-RestMethod http://127.0.0.1:8092/plus/health
```
