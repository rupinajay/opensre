"""Live task-plan checklist for the interactive shell.

The transcript prints a dim toast when the agent revises the plan, and the
full checklist once when every step is still pending. The live prompt overlay
is only the header plus the current step — a six-step list in the prompt
region is reprinted into scrollback on every ``patch_stdout`` tool line.
"""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from core.agent_harness.task_plan.plan import (
    PlanStep,
    PlanStepStatus,
    TaskPlan,
    parse_task_plan,
)
from infrastructure.safety.terminal_output import strip_terminal_controls
from infrastructure.terminal import theme as ui_theme
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


def render_plan_updated(console: Console, plan: TaskPlan | None = None) -> None:
    """Print the transcript toast: ready (nothing ran) or updated (work underway)."""
    console.print()
    if plan is not None and plan.all_pending:
        console.print(Text("Plan ready — nothing executed", style=str(ui_theme.DIM)))
        return
    console.print(Text("Plan updated", style=str(ui_theme.DIM)))


def _overlay_header(plan: TaskPlan) -> str:
    if plan.all_pending:
        return f"Plan ready · 0/{plan.total} executed"
    return f"Plan · {plan.current_index}/{plan.total}"


def _focused_step(plan: TaskPlan) -> PlanStep:
    """The one step the prompt overlay shows: in-progress, else first pending."""
    for item in plan.steps:
        if item.status is PlanStepStatus.IN_PROGRESS:
            return item
    for item in plan.steps:
        if item.status is PlanStepStatus.PENDING:
            return item
    return plan.steps[-1]


def _overlay_line(text: str, style: str, width: int) -> str:
    visible = _clip_text(strip_terminal_controls(text), width)
    return f"{style}{visible}{ui_theme.ANSI_RESET}"


def _step_overlay_line(item: PlanStep, width: int) -> str:
    step = strip_terminal_controls(item.step)
    glyph = _STATUS_GLYPH[item.status]
    if item.status is PlanStepStatus.IN_PROGRESS:
        return _overlay_line(
            f"{glyph} {step}",
            f"{ui_theme.ANSI_BOLD}{ui_theme.TEXT_ANSI}",
            width,
        )
    if item.status is PlanStepStatus.COMPLETED:
        clipped = _clip_text(step, max(width - 2, 1))
        return (
            f"{ui_theme.HIGHLIGHT_ANSI}{glyph} {ui_theme.ANSI_RESET}"
            f"{ui_theme.DIM_ANSI}{clipped}{ui_theme.ANSI_RESET}"
        )
    return _overlay_line(f"{glyph} {step}", ui_theme.DIM_ANSI, width)


def task_plan_overlay_ansi(plan: TaskPlan) -> str:
    """Two-line ANSI overlay: ``Plan · n/m`` plus the current step."""
    width = _prompt_line_width()
    return "\n".join(
        (
            _overlay_line(_overlay_header(plan), ui_theme.SECONDARY_ANSI, width),
            _step_overlay_line(_focused_step(plan), width),
        )
    )


def render_task_plan(console: Console, plan: TaskPlan) -> None:
    """Print the toast plus the full checklist (ready dump and tests)."""
    render_plan_updated(console, plan)
    header = Text()
    header.append(_overlay_header(plan), style=str(ui_theme.SECONDARY))
    console.print(header)
    for item in plan.steps:
        glyph = _STATUS_GLYPH[item.status]
        line = Text()
        if item.status is PlanStepStatus.IN_PROGRESS:
            line.append(f"{glyph} ", style=f"bold {ui_theme.TEXT}")
            line.append(item.step, style=f"bold {ui_theme.TEXT}")
        elif item.status is PlanStepStatus.COMPLETED:
            line.append(f"{glyph} ", style=str(ui_theme.HIGHLIGHT))
            line.append(item.step, style=str(ui_theme.DIM))
        else:
            line.append(f"{glyph} ", style=str(ui_theme.DIM))
            line.append(item.step, style=str(ui_theme.DIM))
        console.print(line)
    if plan.explanation:
        console.print(Text(plan.explanation, style=str(ui_theme.DIM)))
    console.print()


__all__ = [
    "render_plan_updated",
    "render_task_plan",
    "task_plan_from_tool_args",
    "task_plan_overlay_ansi",
]
