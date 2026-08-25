"""Single entry point composing the full terminal UI render.

The terminal UI has four pieces, all composed from this module:

1. splash screen (Braille logo, version, first-run notice)
2. welcome panel (identity column + tips/ambient status)
3. hint/spinner line above the prompt rule
4. prompt rule + ``[n] ❯`` input line

Pieces 1–2 are static chrome printed once by :func:`render_terminal_ui`.
Pieces 3–4 form the live prompt region: prompt-toolkit re-evaluates them on
every keystroke, spinner tick, and prompt invalidation, so they are composed
by :func:`render_prompt_region`, which ``PromptBuilder`` calls per redraw.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import ANSI
from rich.console import Console

from surfaces.interactive_shell.ui.auto_status import auto_status_ansi
from surfaces.interactive_shell.ui.input_prompt import rendering as prompt_rendering
from surfaces.interactive_shell.ui.task_plan import task_plan_overlay_ansi
from surfaces.shared.terminal.banner import render_ready_box, render_splash
from surfaces.shared.terminal.components.cpr_stdin import strip_cpr_sequences

if TYPE_CHECKING:
    from surfaces.interactive_shell.runtime.core.state import ReplState, SpinnerState
    from surfaces.interactive_shell.session import Session


def render_terminal_ui(
    console: Console | None = None,
    *,
    session: object = None,
    first_run: bool | None = None,
) -> None:
    """Render the static terminal chrome: splash screen then welcome panel."""
    console = console or Console(
        highlight=False,
        force_terminal=True,
        color_system="truecolor",
        legacy_windows=False,
    )
    render_splash(console, first_run=first_run)
    render_ready_box(console, session=session)


def render_prompt_region(session: Session, state: ReplState, spinner: SpinnerState) -> ANSI:
    """Compose the live prompt region: plan overlay, status line, rule, input.

    Layout: the two-line ``Plan · n/m`` overlay sits above ``Invoking tools…``
    (or the idle hint), then the input box. ``Plan updated`` is a transcript
    toast, not part of this region.

    The region always starts with one blank row so the overlay/status line never
    sits flush against whatever output scrolled above it. When a plan is
    attached, idle and streaming both include the same two overlay rows, so
    height does not jump between those two states.
    """
    base = prompt_rendering._prompt_message(session).value
    auto_line = strip_cpr_sequences(auto_status_ansi(session))
    if state.is_awaiting_confirmation():
        prefix = state.confirm_prompt_text
    else:
        prefix = strip_cpr_sequences(
            prompt_rendering.resolve_prompt_prefix_ansi(
                inline_spinner=spinner.inline_spinner_ansi(),
                idle_hint=prompt_rendering.resolve_idle_hint_ansi(session),
            )
        )
    plan = getattr(session, "task_plan", None)
    if plan is not None and getattr(plan, "steps", None):
        overlay = strip_cpr_sequences(task_plan_overlay_ansi(plan))
        return ANSI(f"\n{overlay}\n{prefix}\n{auto_line}\n{base}")
    return ANSI(f"\n{prefix}\n{auto_line}\n{base}")


__all__ = ["render_prompt_region", "render_terminal_ui"]
