"""Detect and style human hand-off questions vs the user's answers.

Questions the agent asks the user (a closing ``?``, or a Want-me-to offer)
render in the highlight colour. The user's reply to that question uses the
brand colour so the two are visually distinct in the transcript — the same
split Factory's Droid shell uses for hand-off vs continuation.
"""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from core.agent_harness.session.pending_choice import parse_ask_user_answers
from core.agent_harness.session.want_me_to import WANT_ME_TO_MARKER
from infrastructure.terminal import theme as ui_theme

_QUESTION_MAX_CHARS = 400


def is_handoff_question(text: str) -> bool:
    """True when ``text`` is a short question waiting on the user.

    Structural only: a Want-me-to closer, or a short block whose last line
    ends with ``?``. Does not scan user prose for intent keywords.
    """
    stripped = text.strip()
    if not stripped or stripped.startswith("```"):
        return False
    if WANT_ME_TO_MARKER in stripped.lower():
        return True
    if len(stripped) > _QUESTION_MAX_CHARS:
        return False
    last = ""
    for line in reversed(stripped.splitlines()):
        candidate = line.strip().strip("*").strip()
        if candidate:
            last = candidate
            break
    return last.endswith("?")


def last_assistant_asked_handoff(messages: list[tuple[str, str]]) -> bool:
    """True when the most recent assistant turn is a hand-off question."""
    for role, content in reversed(messages):
        if role == "assistant":
            return is_handoff_question(content)
        if role == "user":
            return False
    return False


def render_handoff_question(console: Console, text: str) -> None:
    """Print a hand-off question in highlight, prefixed with ``?``."""
    body = text.strip()
    line = Text()
    line.append("  ?  ", style=f"bold {ui_theme.HIGHLIGHT}")
    line.append(body, style=str(ui_theme.HIGHLIGHT))
    console.print()
    console.print(line)
    console.print()


def render_handoff_answer_marker() -> Text:
    """Dim marker painted above a submitted answer to a hand-off question."""
    return Text("↗ answer", style=str(ui_theme.DIM))


def render_ask_user_qa(console: Console, pairs: list[tuple[str, str]]) -> None:
    """Print Ask User Q→A: orange header, numbered questions, brand answers."""
    console.print()
    console.print(Text("Ask User", style=f"bold {ui_theme.HIGHLIGHT}"))
    for index, (question, answer) in enumerate(pairs, start=1):
        qline = Text()
        qline.append(f"  {index}.  ", style=str(ui_theme.DIM))
        qline.append(question, style=str(ui_theme.TEXT))
        console.print(qline)
        aline = Text()
        aline.append("      ", style=str(ui_theme.DIM))
        aline.append(answer, style=str(ui_theme.BRAND))
        console.print(aline)
    console.print()


def try_render_ask_user_submission(console: Console, text: str) -> bool:
    """Render a batched Ask User answer block. True when the text matched."""
    pairs = parse_ask_user_answers(text)
    if len(pairs) < 2:
        return False
    render_ask_user_qa(console, pairs)
    return True


def handoff_answer_style() -> str:
    """Brand colour for the user's answer text."""
    return str(ui_theme.BRAND)


__all__ = [
    "handoff_answer_style",
    "is_handoff_question",
    "last_assistant_asked_handoff",
    "render_ask_user_qa",
    "render_handoff_answer_marker",
    "render_handoff_question",
    "try_render_ask_user_submission",
]
