# project-reading-coach 一步到位版

## 放置路径

把整个 `.agents` 目录复制到你的项目根目录：

```text
你的项目/
  .agents/
    skills/
      project-reading-coach/
        SKILL.md
```

## 推荐用法

在 Codex 中进入项目根目录后，直接输入：

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

## 适合你的两类项目

### RAG 项目

它会重点生成：

```text
RAG 请求链路
文档切分 / embedding / 检索 / prompt / LLM 的流程
mini_rag_skeleton
RAG 调试指南
RAG 面试题库
```

### Agent 项目

它会重点生成：

```text
Agent 推理链路
工具调用链路
LangGraph 状态流转
MCP 工具边界
mini_agent_skeleton
mini_langgraph_skeleton
mini_mcp_skeleton
Agent 面试题库
```

## 输出目录

预期生成：

```text
docs/learning/
  00_EXECUTIVE_SUMMARY.md
  01_PROJECT_MAP.md
  02_STARTUP_FLOW.md
  03_REQUEST_FLOW.md
  04_KNOWLEDGE_GAP.md
  05_MINI_SKELETON_PLAN.md
  06_MASTERY_TRACKER.md
  07_QUESTION_BANK.md
  08_FINAL_PROJECT_REVIEW.md
  09_STUDY_PLAN.md
  10_CODE_READING_TASKS.md
  VALIDATION_REPORT.md

learning_skeletons/
  mini_fastapi_skeleton/
  mini_rag_skeleton/
  mini_agent_skeleton/
  mini_langgraph_skeleton/
  mini_mcp_skeleton/
```

实际生成哪些 skeleton，取决于仓库真实使用了哪些技术。

## 只分析不生成骨架

```text
请使用 project-reading-coach 只生成 docs/learning 下的分析文档，暂时不要生成 skeleton。
```

## 只生成题库

```text
请基于 docs/learning/03_REQUEST_FLOW.md 和原项目代码，生成项目掌握度题库。
```

## 注意

这个 Skill 不应该修改你的业务代码。它只应该写入：

```text
docs/learning/
learning_skeletons/
```
