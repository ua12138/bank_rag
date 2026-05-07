# project-reading-coach

## Purpose

Use this skill to turn an unfamiliar Python / FastAPI / RAG / Agent repository into a complete, beginner-readable project reading package in one pass.

The target user profile is:

- knows basic Python syntax, but is weak on advanced Python patterns;
- has limited FastAPI practice;
- has shallow exposure to RAG, LangChain, LangGraph, MCP, ReAct, CoT-style reasoning, and tool-calling agents;
- wants to understand two vibe-coded projects deeply: one RAG project and one Agent project;
- needs concrete code-path explanations, minimal runnable skeletons, debugging guides, knowledge-gap tracking, and question-based mastery evaluation;
- wants materials suitable for Obsidian and interview preparation.

The core learning path is:

```text
repo survey
→ project map
→ startup flow
→ request / pipeline trace
→ knowledge gap map
→ minimal skeleton labs
→ debug guides
→ mastery tracker
→ question bank
→ interview review
```

## Default Behavior

When this skill is invoked, default to **one-shot full learning package generation**.

Unless the user explicitly says "only analyze" or "do not generate skeletons", produce:

```text
docs/learning/00_EXECUTIVE_SUMMARY.md
docs/learning/01_PROJECT_MAP.md
docs/learning/02_STARTUP_FLOW.md
docs/learning/03_REQUEST_FLOW.md
docs/learning/04_KNOWLEDGE_GAP.md
docs/learning/05_MINI_SKELETON_PLAN.md
docs/learning/06_MASTERY_TRACKER.md
docs/learning/07_QUESTION_BANK.md
docs/learning/08_FINAL_PROJECT_REVIEW.md
docs/learning/09_STUDY_PLAN.md
docs/learning/10_CODE_READING_TASKS.md
learning_skeletons/<relevant skeleton folders>/
```

Do not wait for multiple rounds if the repository has enough information. Make a best-effort full package.

## Safety Boundary

Do not modify existing business logic.

Allowed write locations:

```text
docs/learning/
learning_skeletons/
```

Optional allowed files only if useful:

```text
docs/learning/README.md
learning_skeletons/README.md
```

Do not edit:

```text
src/
app/
api/
services/
core/
tests/
config files used by the real app
production scripts
```

If runnable skeletons require dependencies, create separate files inside `learning_skeletons/` only.

## Non-Fabrication Rule

Never claim the project uses FastAPI, LangChain, LangGraph, MCP, RAG, vector database, SQL database, or an Agent framework unless verified from code or dependency files.

If something is not found, write:

```text
Not found in repository.

Possible reasons:
- ...
How to verify:
- ...
```

Do not invent modules, endpoints, classes, or runtime flows.

## Output Style

All documents must be:

- concrete;
- code-path-driven;
- beginner-readable;
- suitable for Obsidian;
- short enough to read section by section;
- tied to actual files, functions, classes, and configuration;
- careful about uncertainty;
- focused on "how the project runs" and "how to learn it";
- not generic architecture writing.

For every important statement about the project, include at least one of:

```text
file path
function name
class name
config key
command
dependency name
```

Prefer including line numbers if easily available.

Use this citation style inside markdown documents:

```text
Code: `path/to/file.py::function_name`
```

When line numbers are available:

```text
Code: `path/to/file.py:L10-L42`
```

## One-Shot Workflow

Follow these steps in order.

---

# Step 0: Repository Survey

Inspect:

- root files;
- package structure;
- README;
- dependency files;
- environment files;
- app startup files;
- test files;
- Docker / compose files;
- scripts;
- API routers;
- services;
- chains;
- graph files;
- tool definitions;
- vector store code;
- database access code;
- MCP server/client code;
- prompt files.

Look for dependency files:

```text
pyproject.toml
requirements.txt
poetry.lock
uv.lock
Pipfile
environment.yml
Dockerfile
docker-compose.yml
```

Classify the project as one or more of:

```text
FastAPI backend
RAG application
Agent application
LangChain application
LangGraph application
MCP tool server/client
Data processing pipeline
CLI application
Other Python service
```

---

# Step 1: Generate Executive Summary

Create:

```text
docs/learning/00_EXECUTIVE_SUMMARY.md
```

Required sections:

```markdown
# Executive Summary

## 1. Project Type

## 2. What This Project Does

## 3. What the Beginner Should Understand First

## 4. Main Runtime Flow

## 5. Most Important Files

## 6. Learning Difficulty Assessment

## 7. Recommended Reading Order

## 8. What Not to Read First
```

Difficulty assessment must use this scale:

```text
Level 1 - basic Python script
Level 2 - FastAPI service
Level 3 - RAG service
Level 4 - Agent / LangGraph / MCP service
Level 5 - production-like AI application
```

Explain why the level was assigned.

---

# Step 2: Generate Project Map

Create:

```text
docs/learning/01_PROJECT_MAP.md
```

Required sections:

```markdown
# Project Map

## 1. One-Sentence Positioning

## 2. Technology Stack

## 3. Directory Structure

## 4. Core Modules

## 5. Runtime Entry Points

## 6. Configuration and Environment

## 7. External Services and Dependencies

## 8. Data Objects and Domain Objects

## 9. Main Runtime Objects

## 10. Dependency Direction

## 11. Beginner Reading Order

## 12. Files to Temporarily Ignore
```

For each core module, use this table:

```markdown
| Module | Responsibility | Important Files | Runtime Role | Beginner Priority |
|---|---|---|---|---|
```

Beginner priority must be one of:

```text
P0 - must read first
P1 - read after main flow
P2 - read after skeleton is understood
P3 - can ignore initially
```

---

# Step 3: Generate Startup Flow

Create:

```text
docs/learning/02_STARTUP_FLOW.md
```

Trace how the app starts.

Required sections:

```markdown
# Startup Flow

## 1. Startup Commands

## 2. Environment Requirements

## 3. Process Startup Sequence

## 4. FastAPI App Creation

## 5. Router Registration

## 6. Service / Chain / Agent Initialization

## 7. External Resource Initialization

## 8. Minimum Startup Path

## 9. Startup Debug Points

## 10. Common Startup Errors
```

For each startup step, use:

```markdown
### Step N: <step name>

- Code:
- Input:
- Output:
- What happens:
- Beginner explanation:
- Debug observation:
```

If no FastAPI app exists, replace FastAPI sections with the actual startup mechanism.

---

# Step 4: Generate Request / Pipeline Flow

Create:

```text
docs/learning/03_REQUEST_FLOW.md
```

Pick the most important runtime path.

If multiple flows exist, choose at most two:

- primary RAG query flow;
- primary Agent execution flow;
- primary FastAPI request flow;
- primary MCP tool call flow.

Required sections:

```markdown
# Request / Pipeline Flow

## 1. Selected Main Flow

## 2. Flow Diagram

## 3. Step-by-Step Trace

## 4. Input / Output Table

## 5. State Changes

## 6. Debug Breakpoints

## 7. Mapping to Minimal Skeleton

## 8. Beginner Explanation
```

Use ASCII diagram.

For a RAG project, trace:

```text
HTTP / CLI input
→ request validation
→ service layer
→ query rewriting if any
→ retriever
→ document recall
→ rerank if any
→ prompt construction
→ LLM call
→ answer assembly
→ response
```

For an Agent project, trace:

```text
HTTP / CLI input
→ state construction
→ planner / LLM call
→ tool selection
→ tool execution
→ observation
→ next reasoning step
→ final answer
→ persistence / callback if any
```

For a LangGraph project, trace:

```text
initial state
→ graph entry node
→ node execution
→ edge / conditional edge
→ state update
→ checkpoint / persistence if any
→ final node
```

For an MCP project, trace:

```text
agent / client
→ MCP client
→ MCP server
→ tool registry
→ tool handler
→ result serialization
→ client receives result
```

Each trace step must include:

```markdown
### Step N: <step name>

- Code:
- Function / class:
- Input:
- Output:
- State before:
- State after:
- Beginner explanation:
- Suggested breakpoint:
```

---

# Step 5: Generate Knowledge Gap Map

Create:

```text
docs/learning/04_KNOWLEDGE_GAP.md
```

Required areas:

```markdown
# Knowledge Gap Map

## 1. Python

## 2. FastAPI

## 3. Pydantic / Data Validation

## 4. RAG

## 5. Embedding / Vector Store / Retrieval

## 6. Prompt Engineering

## 7. LangChain

## 8. LangGraph

## 9. Agent / ReAct / Tool Calling

## 10. MCP

## 11. Database / Storage

## 12. Async / Concurrency

## 13. Engineering / Deployment / Debugging
```

Only include areas that are actually relevant. If an area is not relevant, mark it as "Not used in this repository".

For each knowledge point, use this table:

```markdown
| Knowledge Point | Code Location | Why This Project Needs It | Required Level | Exercise |
|---|---|---|---|---|
```

Required level must be one of:

```text
A - recognize only
B - explain conceptually
C - debug existing code
D - modify existing code
E - implement minimal version from scratch
F - explain in interview
```

Exercises must be small and project-specific.

Bad exercise:

```text
Learn FastAPI.
```

Good exercise:

```text
Hand-code a `/chat` endpoint that receives `question: str`, calls a service function, and returns `{answer: ...}`. Compare it with `path/to/router.py`.
```

---

# Step 6: Generate Minimal Skeleton Plan

Create:

```text
docs/learning/05_MINI_SKELETON_PLAN.md
```

The plan must decompose the original project into small runnable labs.

Candidate skeletons:

```text
mini_fastapi_skeleton
mini_rag_skeleton
mini_agent_skeleton
mini_langgraph_skeleton
mini_mcp_skeleton
mini_storage_skeleton
```

Only generate relevant skeletons.

For each skeleton, include:

```markdown
## <Skeleton Name>

### Learning Goal

### Original Project Mapping

### File Structure

### Run Command

### Debug Points

### Hand-Code Tasks

### Completion Standard
```

---

# Step 7: Generate Skeleton Code

Create skeletons under:

```text
learning_skeletons/
```

Only generate minimal code, not a miniature copy of the whole project.

General rules:

- keep each file small;
- use deterministic mock data where possible;
- avoid requiring external API keys;
- avoid real paid LLM calls unless the original project already has a safe mock path;
- include comments for beginner-level concepts;
- include `README.md`;
- include `DEBUG_GUIDE.md`;
- include a runnable command;
- include a mapping back to original project;
- include a small expected output example;
- prefer simple Python standard library logic when external dependencies are unnecessary.

## FastAPI Skeleton

Generate if the project uses FastAPI.

Target:

```text
learning_skeletons/mini_fastapi_skeleton/
  README.md
  DEBUG_GUIDE.md
  main.py
  schemas.py
  routers/
    chat.py
  services/
    chat_service.py
```

Demonstrate:

```text
request body
→ Pydantic schema
→ router
→ service
→ response
```

## RAG Skeleton

Generate if the project contains retrieval, embedding, vector stores, document parsing, QA chains, or knowledge base code.

Target:

```text
learning_skeletons/mini_rag_skeleton/
  README.md
  DEBUG_GUIDE.md
  main.py
  documents.py
  splitter.py
  embedding.py
  vector_store.py
  retriever.py
  qa_chain.py
```

Demonstrate:

```text
documents
→ chunks
→ mock embeddings
→ vector store
→ retrieval
→ prompt assembly
→ mock answer
```

Use mock embeddings if possible.

## Agent Skeleton

Generate if the project contains tools, agent executors, ReAct logic, function calling, tool selection, operation diagnosis, or planner-executor logic.

Target:

```text
learning_skeletons/mini_agent_skeleton/
  README.md
  DEBUG_GUIDE.md
  main.py
  agent.py
  state.py
  prompts.py
  tools/
    metric_tool.py
    change_tool.py
    case_search_tool.py
```

Demonstrate:

```text
question
→ simple plan
→ choose tool
→ call tool
→ observation
→ final answer
```

Use deterministic rule-based planning if real LLM calls are not needed.

## LangGraph Skeleton

Generate if the project contains LangGraph.

Target:

```text
learning_skeletons/mini_langgraph_skeleton/
  README.md
  DEBUG_GUIDE.md
  main.py
  graph.py
  state.py
  nodes/
    plan_node.py
    tool_node.py
    analyze_node.py
    final_node.py
```

Demonstrate:

```text
State
→ Node
→ Edge
→ Conditional Edge
→ State Update
→ Final
```

If importing LangGraph would create dependency problems, provide a minimal pure-Python graph simulator and clearly state that it is a learning skeleton, not a framework replacement.

## MCP Skeleton

Generate if the project contains MCP server/client/tool code.

Target:

```text
learning_skeletons/mini_mcp_skeleton/
  README.md
  DEBUG_GUIDE.md
  server.py
  client.py
  tools/
    search_manual.py
```

Demonstrate:

```text
client request
→ tool registry
→ tool handler
→ serialized result
```

If the actual MCP SDK is not available, create a simplified local simulation and clearly mark it as a learning simulation.

---

# Step 8: Generate Debug Guides

Each skeleton must include:

```text
DEBUG_GUIDE.md
```

Required sections:

```markdown
# Debug Guide

## 1. Run Command

## 2. Test Input

## 3. Expected Output

## 4. Breakpoint Table

| Breakpoint | File | Function | Observe Variable | Expected Value | Why It Matters |
|---|---|---|---|---|---|

## 5. Step-by-Step Debug Path

## 6. Common Errors

## 7. Mapping Back to Original Project
```

Breakpoints must be concrete.

Bad:

```text
Set breakpoint in service layer.
```

Good:

```text
Set breakpoint at `services/chat_service.py::answer_question`.
Observe `question`, `retrieved_docs`, and `final_prompt`.
```

---

# Step 9: Generate Mastery Tracker

Create:

```text
docs/learning/06_MASTERY_TRACKER.md
```

Required format:

```markdown
# Mastery Tracker

| Area | Knowledge Point | Code Location | Current Level | Evidence Required | Next Action |
|---|---|---|---|---|---|
```

Current level must be initialized conservatively:

```text
0 - unfamiliar
1 - can recognize
2 - can explain
3 - can debug
4 - can modify
5 - can implement and explain in interview
```

Because the user is a beginner, most advanced areas should start at 0 or 1 unless the project is trivial.

Evidence examples:

```text
Can draw request flow without notes.
Can explain why schema validation happens before service execution.
Can hand-code a mock retriever.
Can set breakpoints and inspect state changes.
Can explain Agent tool observation in interview.
```

---

# Step 10: Generate Question Bank

Create:

```text
docs/learning/07_QUESTION_BANK.md
```

Required sections:

```markdown
# Question Bank

## 1. Basic Understanding

## 2. Code Reading

## 3. Debugging

## 4. Implementation

## 5. Architecture

## 6. Interview Explanation

## 7. Self-Test Scoring Rubric
```

For each question, include:

```markdown
### Q<N>. <Question>

- Type:
- Related code:
- Expected answer:
- What a weak answer misses:
- Scoring:
```

Question count guidance:

- small project: 20-30 questions;
- medium project: 30-50 questions;
- large project: 50-80 questions.

Do not generate trivial questions only. Include code-reading and debugging questions.

---

# Step 11: Generate Final Project Review

Create:

```text
docs/learning/08_FINAL_PROJECT_REVIEW.md
```

Required sections:

```markdown
# Final Project Review

## 1. Project Background

## 2. Architecture Summary

## 3. Main Flow Explanation

## 4. Core Technical Decisions

## 5. Difficult Points

## 6. Engineering Tradeoffs

## 7. Interview-Ready Version

## 8. Risks in Overclaiming

## 9. What I Still Need to Learn
```

"Risks in Overclaiming" is mandatory. It must prevent the user from saying things in interviews that the code does not support.

Example:

```text
Do not claim distributed scheduling exists unless the repository contains worker queue / task table / scheduler code.
```

---

# Step 12: Generate Study Plan

Create:

```text
docs/learning/09_STUDY_PLAN.md
```

The plan must be practical for the user.

Required sections:

```markdown
# Study Plan

## 1. Study Goal

## 2. 7-Day Minimum Plan

## 3. 14-Day Standard Plan

## 4. Daily Output Checklist

## 5. What to Ask ChatGPT After Each Day

## 6. What to Ask Codex After Each Day
```

The plan must follow this learning order:

```text
run project
→ read startup flow
→ read main request flow
→ hand-code skeleton
→ debug skeleton
→ map skeleton back to original code
→ answer questions
→ prepare interview explanation
```

---

# Step 13: Generate Code Reading Tasks

Create:

```text
docs/learning/10_CODE_READING_TASKS.md
```

Required sections:

```markdown
# Code Reading Tasks

## 1. P0 Tasks - Main Flow

## 2. P1 Tasks - Core Modules

## 3. P2 Tasks - Supporting Modules

## 4. P3 Tasks - Optional / Later

## 5. Verification Tasks

## 6. Refuse-to-Overclaim Checklist
```

Each task must include:

```markdown
### Task N: <task>

- Read:
- Goal:
- Questions to answer:
- Debug action:
- Completion standard:
```

---

# Step 14: Validation

After writing files:

1. Check that all required files exist.
2. Check that each skeleton has `README.md` and `DEBUG_GUIDE.md`.
3. If safe and dependencies permit, run a minimal command for each skeleton.
4. If not run, write why not in the skeleton README.
5. Do not claim validation succeeded unless a command was actually executed.

Create:

```text
docs/learning/VALIDATION_REPORT.md
```

Required sections:

```markdown
# Validation Report

## 1. Files Generated

## 2. Skeletons Generated

## 3. Commands Executed

## 4. Commands Not Executed

## 5. Known Gaps

## 6. Next Recommended Command
```

---

# Final Response Format to User

When done, respond with a concise summary:

```markdown
已完成项目精读包生成。

## 生成文件

- ...
- ...

## 骨架项目

- ...

## 已验证

- ...

## 未验证 / 不确定

- ...

## 下一步建议

请先打开 `docs/learning/00_EXECUTIVE_SUMMARY.md`，再按 `09_STUDY_PLAN.md` 执行。
```

Do not paste all document contents into chat unless the user asks.

## Invocation Examples

### One-shot full package

```text
请使用 project-reading-coach 对当前仓库做一步到位的项目精读包生成。

要求：
1. 不修改业务代码
2. 输出 docs/learning 下的完整学习文档
3. 输出 learning_skeletons 下的最小骨架
4. 每个骨架都要有 DEBUG_GUIDE.md
5. 输出 QUESTION_BANK 和 MASTERY_TRACKER
6. 输出最终面试复盘文档
```

### Analyze only

```text
请使用 project-reading-coach 只生成 docs/learning 下的分析文档，暂时不要生成 skeleton。
```

### Skeleton only

```text
请基于 docs/learning/05_MINI_SKELETON_PLAN.md，只生成 mini_rag_skeleton 和 DEBUG_GUIDE.md，不要改业务代码。
```

### Question bank only

```text
请基于 docs/learning/03_REQUEST_FLOW.md 和原项目代码，生成项目掌握度题库。
```

## Completion Criteria

The one-shot task is complete only when all of these exist:

```text
docs/learning/00_EXECUTIVE_SUMMARY.md
docs/learning/01_PROJECT_MAP.md
docs/learning/02_STARTUP_FLOW.md
docs/learning/03_REQUEST_FLOW.md
docs/learning/04_KNOWLEDGE_GAP.md
docs/learning/05_MINI_SKELETON_PLAN.md
docs/learning/06_MASTERY_TRACKER.md
docs/learning/07_QUESTION_BANK.md
docs/learning/08_FINAL_PROJECT_REVIEW.md
docs/learning/09_STUDY_PLAN.md
docs/learning/10_CODE_READING_TASKS.md
docs/learning/VALIDATION_REPORT.md
```

If skeletons are relevant, each generated skeleton must include:

```text
README.md
DEBUG_GUIDE.md
runnable code or clearly marked simulated code
mapping back to original project
```
