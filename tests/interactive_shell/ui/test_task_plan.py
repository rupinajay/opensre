"""Factory Droid-style task-plan checklist rendering."""

from __future__ import annotations

import io
import re

from rich.console import Console

from core.agent_harness.task_plan.plan import parse_task_plan
from surfaces.interactive_shell.runtime.core.state import ReplState, SpinnerState
from surfaces.interactive_shell.session import Session
from surfaces.interactive_shell.ui.task_plan import (
    render_plan_updated,
    render_task_plan,
    task_plan_overlay_ansi,
)
from surfaces.interactive_shell.ui.terminal_ui import render_prompt_region


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _sample_plan():
    plan, error = parse_task_plan(
        {
            "plan": [
                {"step": "Capture 502 samples from checkout", "status": "completed"},
                {"step": "Trace 502s to the last deploy", "status": "in_progress"},
                {"step": "Confirm checkout returns 2xx", "status": "pending"},
            ]
        }
    )
    assert error is None and plan is not None
    return plan


def test_render_task_plan_shows_counter_and_status_glyphs() -> None:
    plan = _sample_plan()
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, highlight=False, width=80)
    render_task_plan(console, plan)
    output = buffer.getvalue()
    assert "Plan updated" in output
    assert "Plan · 2/3" in output
    assert "✓" in output
    assert "●" in output
    assert "○" in output
    assert "(verify)" not in output
    assert "Confirm checkout returns 2xx" in output


def test_plan_updated_toast_is_the_transcript_line() -> None:
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, highlight=False, width=80)
    render_plan_updated(console)
    assert buffer.getvalue().strip() == "Plan updated"


def test_task_plan_overlay_matches_factory_checklist() -> None:
    overlay = _strip_ansi(task_plan_overlay_ansi(_sample_plan()))
    assert overlay.startswith("Plan · 2/3")
    assert "✓ Capture 502 samples from checkout" in overlay
    assert "● Trace 502s to the last deploy" in overlay
    assert "○ Confirm checkout returns 2xx" in overlay


def test_prompt_region_keeps_the_checklist_above_invoking_tools() -> None:
    session = Session()
    session.task_plan = _sample_plan()
    spinner = SpinnerState()
    spinner.start()
    spinner.set_phase(SpinnerState.INVOKING_TOOLS_PHASE)
    rendered = _strip_ansi(render_prompt_region(session, ReplState(), spinner).value)
    assert "Plan updated" not in rendered
    assert "Plan · 2/3" in rendered
    assert "● Trace 502s to the last deploy" in rendered
    assert SpinnerState.INVOKING_TOOLS_PHASE in rendered
    assert rendered.index("Plan · 2/3") < rendered.index(SpinnerState.INVOKING_TOOLS_PHASE)
    assert "Auto (High)" in rendered
    assert rendered.index(SpinnerState.INVOKING_TOOLS_PHASE) < rendered.index("Auto (High)")
