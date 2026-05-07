# API DEBUG GUIDE

1. `/health` 不通：先看服务是否启动、端口是否冲突。  
2. `/query` 400：看请求体字段是否缺失（`api/schemas.py`）。  
3. `/query` 500：优先排查 service 层异常。
