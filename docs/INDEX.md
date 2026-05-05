# 文档统一入口（INDEX）

本文件用于统一 `docs/` 与 `spec/` 的阅读顺序，并给出去重导航，避免重复阅读同类内容。

## 1. 推荐阅读顺序

1. 运行与快速操作：`README.md`
2. 技术架构与实现细节：`spec/DEV_SPEC.md`
3. 验收与排查：`spec/ACCEPTANCE.md`
4. 接口契约：`spec/openapi.yaml`
5. 代码走读（函数级）：`docs/code_reading/PROJECT_MAP.md` -> `STARTUP_FLOW.md` -> `REQUEST_FLOW.md`
6. 性能评估：`docs/code_reading/PERF_AB_EVAL.md`
7. 小白学习路径：`docs/code_reading/BEGINNER_GUIDE.md`

## 2. 去重导航（同主题主文档）

### 主题 A：系统真实实现
- 主文档：`spec/DEV_SPEC.md`
- 辅助文档：`docs/project_intelligence.md`
- 规则：涉及实现细节、调用链、策略参数时，以 `DEV_SPEC.md` 为准。

### 主题 B：代码链路走读
- 主文档：
  - `docs/code_reading/PROJECT_MAP.md`
  - `docs/code_reading/STARTUP_FLOW.md`
  - `docs/code_reading/REQUEST_FLOW.md`
- 规则：函数级证据只放在这 3 份文档，其他文档不重复展开。

### 主题 C：操作与验收
- 主文档：
  - `README.md`（怎么操作）
  - `spec/ACCEPTANCE.md`（怎么验收和排查）

### 主题 D：性能 A/B
- 主文档：`docs/code_reading/PERF_AB_EVAL.md`
- 数据结果：`reports/perf_ab_report_*.json|md`
- 规则：评估方法写在文档，结果只保存在 `reports/`。

### 主题 E：学习与面试
- 主文档：`docs/code_reading/BEGINNER_GUIDE.md`
- 辅助文档：`docs/interview_bank.md`
- 状态记录：`docs/session_state.md`

## 3. 为什么不合并 `spec/` 和 `docs/`

- `spec/`：规范、契约、验收基线（必须遵守）
- `docs/`：阅读、学习、走读资料（便于理解）

两类文档目标不同，保留双目录更利于长期维护。
