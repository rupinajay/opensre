"""Plain-text task-plan formatting (prompts, logs, non-TTY).

Rich rendering lives in
``surfaces.interactive_shell.ui.task_plan``.
"""

from __future__ import annotations

from core.agent_harness.task_plan.plan import PlanStepStatus, TaskPlan

_STATUS_MARK: dict[PlanStepStatus, str] = {
    PlanStepStatus.COMPLETED: "✓",
    PlanStepStatus.IN_PROGRESS: "●",
    PlanStepStatus.PENDING: "○",
}


def format_task_plan_plain(plan: TaskPlan) -> str:
    """Checklist with ``Plan · n/m`` header and ✓ / ● / ○ step marks."""
    if plan.all_pending:
        header = f"Plan ready · 0/{plan.total} executed"
    else:
        header = f"Plan · {plan.current_index}/{plan.total}"
    lines = [header]
    last_index = plan.total - 1
    for index, item in enumerate(plan.steps):
        mark = _STATUS_MARK[item.status]
        suffix = "  (verify)" if index == last_index else ""
        lines.append(f"  {mark} {item.step}{suffix}")
    return "\n".join(lines)


__all__ = ["format_task_plan_plain"]
