from __future__ import annotations

"""混合意图工作流：把问答、工具检索、行动方案串成流程。"""

from dataclasses import dataclass
from typing import Any, Callable

from RAG_PLUS.mcp_registry import MCPRegistry


@dataclass
class WorkflowStep:
    """工作流步骤定义。"""

    step_id: str
    name: str
    depends_on: list[str]
    detail: str


class MixedIntentWorkflowEngine:
    """混合意图执行引擎。

    1) 意图识别
    2) 计划拆解
    3) 执行与聚合
    """

    def detect_intents(self, query: str) -> list[str]:
        """从查询中识别意图标签。"""
        text = (query or "").strip()
        intents = ["qa"]

        if any(token in text for token in ["调用", "接口", "工单", "服务", "工具"]):
            intents.append("tool_lookup")
        if any(token in text for token in ["报告", "总结", "汇总", "看板"]):
            intents.append("report")
        if any(token in text for token in ["执行", "变更", "重启", "修复"]):
            intents.append("action_plan")
        return intents

    def build_plan(self, intents: list[str]) -> list[WorkflowStep]:
        """根据意图生成步骤 DAG（简化版）。"""
        steps: list[WorkflowStep] = [
            WorkflowStep(step_id="s1", name="retrieve_and_answer", depends_on=[], detail="先基于知识库回答主问题")
        ]
        if "tool_lookup" in intents:
            steps.append(WorkflowStep(step_id="s2", name="find_tools", depends_on=["s1"], detail="从 MCP 注册中心检索可用工具"))
        if "action_plan" in intents:
            steps.append(WorkflowStep(step_id="s3", name="build_action_plan", depends_on=["s1"], detail="生成可执行操作方案并提示风险"))
        if "report" in intents:
            steps.append(
                WorkflowStep(
                    step_id="s4",
                    name="build_report",
                    depends_on=[step.step_id for step in steps],
                    detail="将问答和工具建议汇总成报告",
                )
            )
        return steps

    def run(
        self,
        query: str,
        kb_id: str,
        qa_callable: Callable[..., dict[str, Any]],
        registry: MCPRegistry,
        caller_scopes: list[str],
        top_k: int,
        candidate_multiplier: int,
        session_id: str = "",
    ) -> dict[str, Any]:
        """执行混合意图工作流。"""
        intents = self.detect_intents(query)
        plan = self.build_plan(intents)

        qa_result = qa_callable(
            kb_id=kb_id,
            query=query,
            top_k=top_k,
            candidate_multiplier=candidate_multiplier,
            session_id=session_id,
        )

        tools = []
        if "tool_lookup" in intents:
            tools = registry.search(query=query, caller_scopes=caller_scopes, limit=5)

        action_plan = []
        if "action_plan" in intents:
            action_plan = [
                "1) 先确认影响范围与回滚条件",
                "2) 在低峰窗口执行变更，保留审计日志",
                "3) 出现异常立刻按回滚方案恢复",
            ]

        report = ""
        if "report" in intents:
            report = (
                "混合意图执行报告：\n"
                f"- 主答案摘要：{qa_result.get('answer', '')[:180]}\n"
                f"- 候选工具数量：{len(tools)}\n"
                f"- 是否包含行动建议：{'是' if action_plan else '否'}"
            )

        return {
            "intents": intents,
            "plan": [step.__dict__ for step in plan],
            "qa": qa_result,
            "tools": tools,
            "action_plan": action_plan,
            "report": report,
        }
