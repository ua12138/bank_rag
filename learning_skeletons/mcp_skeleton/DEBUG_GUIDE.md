# MCP DEBUG GUIDE

1. tools/list 为空：检查 `_tool_specs()` 是否正确返回。  
2. tools/call 报参数错误：检查 `arguments` 是否是对象。  
3. method not found：检查 JSON-RPC `method` 拼写。
