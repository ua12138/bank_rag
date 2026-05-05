# 02｜启动链路（你要能背下来）

## 启动入口 A：基础服务
- 文件：`src/hz_bank_rag/api/main.py`
- 函数：`build_app()`

### 关键装配顺序
1. `MetadataStore(settings.sqlite_path)`  
2. `BM25Store()`  
3. `MilvusVectorStore(...)` 或 `InMemoryVectorStore(...)`  
4. `RAGRepository(metadata, vector_store, bm25)`  
5. `HybridRetriever(bm25_store, vector_store)`  
6. `QAService(repo, retriever, rewriter, reranker, meta)`  
7. 注册 HTTP 路由（`/query`、`/demo/seed`、`/evaluate/*` 等）

## 启动入口 B：MCP 包装服务
- 文件：`src/hz_bank_rag/mcp/main.py`
- 函数：`build_mcp_app()`
- 作用：把基础能力包装成 MCP / JSON-RPC 的工具调用风格

## 启动入口 C：增强版 RAG_PLUS
- 文件：`RAG_PLUS/main.py`
- 函数：`build_app()`
- 新增能力：鉴权、限流、并发槽位、智能路由、MCP 注册中心、workflow

## ASCII 启动图
```text
uvicorn hz_bank_rag.api.main:app
    -> build_app()
    -> 初始化 store/repo/retriever/service
    -> 路由可用

uvicorn hz_bank_rag.mcp.main:app
    -> build_mcp_app()
    -> runtime + tool specs
    -> /mcp JSON-RPC 可用

uvicorn RAG_PLUS.main:app
    -> build_app()
    -> auth + redis + router + workflow
    -> /plus/* 可用
```

## 容易混淆点
- `src/hz_bank_rag/*` 是“基础能力主实现”
- `RAG_PLUS/*` 是“增强编排层”
- 两者都可独立启动，不是互相覆盖关系
