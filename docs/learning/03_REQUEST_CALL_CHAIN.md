# 03 请求调用链路（小白版）

## 1. 三个入口
1. `POST /query`
2. `POST /knowledge-bases/{kb_id}/documents`
3. `POST /plus/query`

## 2. 问答链路
- API 接收问题 -> QAService.ask -> 检索 -> 生成 -> 返回答案与证据

## 3. 入库链路
- 解析 -> 清洗 -> 切块 -> 写元数据与向量 -> 更新 BM25

## 4. RAG_PLUS 链路
- 鉴权 -> 限流与并发保护 -> 智能路由 -> 问答

## 5. 规划能力
- KG 证据增强
- 阶段耗时与 token 统计
- UI: `/ui/kg`、`/ui/metrics`
