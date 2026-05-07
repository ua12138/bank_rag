# Codex Prompts

## 一步到位生成项目精读包

```text
请使用 project-reading-coach 对当前仓库做一步到位的项目精读包生成。

我的背景：
- Python 只掌握基础语法
- FastAPI 没有实战经验
- RAG / Agent / LangChain / LangGraph / MCP 只了解基础概念
- 目标是吃透这个项目，而不是泛泛总结

要求：
1. 不修改业务代码
2. 输出 docs/learning 下的完整学习文档
3. 输出 learning_skeletons 下的最小骨架
4. 每个骨架都要有 DEBUG_GUIDE.md
5. 输出 QUESTION_BANK 和 MASTERY_TRACKER
6. 输出最终面试复盘文档
7. 如果无法验证运行，明确写进 VALIDATION_REPORT.md
```

## 只分析当前仓库

```text
请使用 project-reading-coach 只生成 docs/learning 下的分析文档，暂时不要生成 skeleton。
```

## 基于已有分析补骨架

```text
请基于 docs/learning/05_MINI_SKELETON_PLAN.md 生成相关 learning_skeletons。不要改业务代码。
```

## 基于已有分析补题库

```text
请基于 docs/learning/03_REQUEST_FLOW.md、04_KNOWLEDGE_GAP.md 和原项目代码，生成 docs/learning/07_QUESTION_BANK.md。
```
