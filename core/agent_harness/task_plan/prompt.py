"""Prompt fragments for the live task plan.

The STABLE planning instructions live in ``planning_instructions.md``. This
module renders the per-turn CURRENT PLAN block from the snapshotted plan so
transcript compaction cannot drop it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from core.agent_harness.session.pending_choice import parse_ask_user_answers
from core.agent_harness.task_plan.plan import PlanStepStatus, TaskPlan
from core.agent_harness.task_plan.progress import format_task_plan_plain

ASK_USER_ANSWERED_GUIDANCE = (
    "ASK USER JUST ANSWERED (this turn). Continue — do not sit idle. "
    "If facts still block a plan, call ask_user_choice once more. "
    "Otherwise write facts and a hypothesis table, then update_plan. "
    "If the user said not to run yet, every step pending then STOP — do not "
    "repeat the checklist in prose. Otherwise first step in_progress and "
    "execute. Answering is the go-ahead to continue."
)

_INSTRUCTIONS_FILENAME = "planning_instructions.md"


@lru_cache(maxsize=1)
def load_planning_instructions() -> str:
    """Return the bundled planning-instruction markdown."""
    path = Path(__file__).with_name(_INSTRUCTIONS_FILENAME)
    return path.read_text(encoding="utf-8")


def ask_user_answered_block(text: str) -> str:
    """Ephemeral start-now rule when this turn is structured Ask User answers."""
    if not parse_ask_user_answers(text):
        return ""
    return ASK_USER_ANSWERED_GUIDANCE


def current_task_plan_block(plan: TaskPlan | None) -> str:
    """Render the CURRENT PLAN block, or ``""`` when no plan is attached."""
    if plan is None or not plan.steps:
        return ""
    if plan.all_completed:
        status = "complete"
    elif plan.all_pending:
        status = "ready, nothing executed"
    else:
        status = "in progress"
    lines = [
        f"CURRENT PLAN ({status}; Plan · {plan.current_index}/{plan.total}). "
        "This is the durable record — older messages may have dropped an "
        "earlier version. Keep it current with update_plan; do not recreate "
        "it from memory.",
        format_task_plan_plain(plan),
    ]
    if plan.explanation:
        lines.append(f"explanation: {plan.explanation}")
    in_progress = next(
        (item.step for item in plan.steps if item.status is PlanStepStatus.IN_PROGRESS),
        None,
    )
    if in_progress is not None:
        lines.append(f"now: {in_progress}")
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "ASK_USER_ANSWERED_GUIDANCE",
    "_INSTRUCTIONS_FILENAME",
    "ask_user_answered_block",
    "current_task_plan_block",
    "load_planning_instructions",
]
