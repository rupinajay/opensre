"""Factory Droid-style live task-plan checklist for the interactive shell.

Factory's transcript prints a dim ``Plan updated`` toast when the agent
revises the plan. The ``Plan · n/m`` checklist itself is a live overlay
above the spinner / input — ✓ and ○ dimmed, ● current step in bright body
text — so compaction of scrollback cannot hide progress.
"""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from core.agent_harness.task_plan.plan import PlanStepStatus, TaskPlan, parse_task_plan
from infrastructure.terminal import theme as ui_theme
from infrastructure.terminal.theme import DIM, HIGHLIGHT, SECONDARY, TEXT
from surfaces.interactive_shell.ui.input_prompt.layout import _clip_text, _prompt_line_width

_STATUS_GLYPH: dict[PlanStepStatus, str] = {
    PlanStepStatus.COMPLETED: "✓",
    PlanStepStatus.IN_PROGRESS: "●",
    PlanStepStatus.PENDING: "○",
}


def task_plan_from_tool_args(args: dict[str, object]) -> TaskPlan | None:
    """Parse a plan from an ``update_plan`` tool-call payload."""
    if not isinstance(args, dict):
        return None
    plan, _error = parse_task_plan(args)
    return plan


def render_plan_updated(console: Console) -> None:
    """Print Factory's dim ``Plan updated`` toast in the transcript."""
    console.print()
    console.print(Text("Plan updated", style=str(DIM)))


def _overlay_line(text: str, style: str, width: int) -> str:
    return f"{style}{_clip_text(text, width)}{ui_theme.ANSI_RESET}"


def task_plan_overlay_ansi(plan: TaskPlan) -> str:
    """ANSI ``Plan · n/m`` checklist for the live prompt region."""
    width = _prompt_line_width()
    lines = [
        _overlay_line(
            f"Plan · {plan.current_index}/{plan.total}",
            ui_theme.SECONDARY_ANSI,
            width,
        )
    ]
    for item in plan.steps:
        glyph = _STATUS_GLYPH[item.status]
        body = f"{glyph} {item.step}"
        if item.status is PlanStepStatus.IN_PROGRESS:
            style = f"{ui_theme.ANSI_BOLD}{ui_theme.TEXT_ANSI}"
            lines.append(_overlay_line(body, style, width))
        elif item.status is PlanStepStatus.COMPLETED:
            step = _clip_text(item.step, max(width - 2, 1))
            lines.append(
                f"{ui_theme.HIGHLIGHT_ANSI}{glyph} {ui_theme.ANSI_RESET}"
                f"{ui_theme.DIM_ANSI}{step}{ui_theme.ANSI_RESET}"
            )
        else:
            lines.append(_overlay_line(body, ui_theme.DIM_ANSI, width))
    return "\n".join(lines)


def render_task_plan(console: Console, plan: TaskPlan) -> None:
    """Print the toast plus the checklist (tests and non-prompt dumps)."""
    render_plan_updated(console)
    header = Text()
    header.append("Plan · ", style=str(SECONDARY))
    header.append(f"{plan.current_index}/{plan.total}", style=str(SECONDARY))
    console.print(header)
    for item in plan.steps:
        glyph = _STATUS_GLYPH[item.status]
        line = Text()
        if item.status is PlanStepStatus.IN_PROGRESS:
            line.append(f"{glyph} ", style=f"bold {TEXT}")
            line.append(item.step, style=f"bold {TEXT}")
        elif item.status is PlanStepStatus.COMPLETED:
            line.append(f"{glyph} ", style=str(HIGHLIGHT))
            line.append(item.step, style=str(DIM))
        else:
            line.append(f"{glyph} ", style=str(DIM))
            line.append(item.step, style=str(DIM))
        console.print(line)
    if plan.explanation:
        console.print(Text(plan.explanation, style=str(DIM)))
    console.print()


__all__ = [
    "render_plan_updated",
    "render_task_plan",
    "task_plan_from_tool_args",
    "task_plan_overlay_ansi",
]
