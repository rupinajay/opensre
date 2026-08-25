"""Create, revise, and mark steps on the agent's live task plan."""

from __future__ import annotations

from typing import Any

from core.agent_harness.task_plan.plan import parse_task_plan, task_plan_to_payload
from core.agent_harness.task_plan.progress import format_task_plan_plain
from core.agent_harness.tools import ActionToolScope, execute_with_action_context
from core.domain.types.tools import ToolSurface
from core.tool import RegisteredTool, SideEffectLevel
from core.tool_framework.utils import object_schema, string_property

_PLAN_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "step": string_property(
            description="One short observable outcome (about 5–10 words).",
            min_length=1,
        ),
        "status": string_property(
            description="One of: pending, in_progress, completed.",
            enum=("pending", "in_progress", "completed"),
        ),
    },
    "required": ["step", "status"],
    "additionalProperties": False,
}


def execute_update_plan_tool(args: dict[str, Any], ctx: ActionToolScope) -> dict[str, Any]:
    plan, error = parse_task_plan(args)
    if error is not None or plan is None:
        return {"ok": False, "error": error or "invalid plan"}
    ctx.session.task_plan = plan
    payload = task_plan_to_payload(plan)
    payload["ok"] = True
    payload["summary"] = format_task_plan_plain(plan)
    payload["instruction"] = (
        "Plan stored. Keep it current with update_plan; the CURRENT PLAN "
        "block is the durable record when older messages drop."
    )
    return payload


def run_update_plan(
    *,
    plan: list[dict[str, Any]] | None = None,
    explanation: str | None = None,
    context: Any,
) -> dict[str, Any]:
    args: dict[str, Any] = {"plan": plan or []}
    if explanation is not None:
        args["explanation"] = explanation
    return execute_with_action_context(args, context, execute_update_plan_tool)


update_plan_tool = RegisteredTool(
    name="update_plan",
    description=(
        "Create or revise the live execution plan for this workload, and mark "
        "steps pending, in_progress, or completed. Call this BEFORE executing "
        "any multi-step workload. The last step must be a verification check. "
        "At most one step may be in_progress. Not for durable human todos "
        "(use work_task_*) and not for /goal keep-going."
    ),
    use_cases=[
        "A multi-step investigation, fix, and verify workload is about to start",
        "A step just finished and the next step is starting",
        "The plan changed and the checklist must be revised",
        "The user asked for a plan only, with no execution yet",
    ],
    anti_examples=[
        "A single obvious lookup or one slash command",
        "Durable human todos / reminders (use work_task_add)",
        "Session-goal keep-going checklists (assistant_handoff session_goal)",
    ],
    input_schema=object_schema(
        properties={
            "explanation": string_property(
                description=("Optional rationale shown when the plan is created or revised."),
            ),
            "plan": {
                "type": "array",
                "description": (
                    "Ordered steps. Last item is always the verification check. "
                    "At most one status may be in_progress."
                ),
                "items": _PLAN_ITEM_SCHEMA,
                "minItems": 2,
            },
        },
        required=("plan",),
    ),
    source="interactive_shell",
    surfaces=(ToolSurface.ACTION,),
    parallel_safe=False,
    accepts_runtime_context=True,
    run=run_update_plan,
    tags=("safe", "fast", "no-credentials"),
    side_effect_level=SideEffectLevel.READ_ONLY,
)


__all__ = [
    "execute_update_plan_tool",
    "run_update_plan",
    "update_plan_tool",
]
