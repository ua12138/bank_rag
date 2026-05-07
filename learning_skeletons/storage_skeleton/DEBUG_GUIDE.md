# Storage DEBUG GUIDE

1. 入库报重复：看 content_hash / near_hash 判定。  
2. 删除后搜不到历史：看 family 激活逻辑是否触发。  
3. SQLite 无数据：看 `settings.sqlite_path` 是否正确。
