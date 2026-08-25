"""Paint Droid-style charts inside assistant markdown.

Investigation answers land as markdown. A wall of prose is hard to scan.
This module detects sparklines, attribution bars, deploy-align markers, and
GitHub tables and renders them with the semantic palette; everything else
stays Rich Markdown.
"""

from __future__ import annotations

import re

from rich.box import SIMPLE
from rich.console import Console
from rich.table import Table
from rich.text import Text

from infrastructure.terminal.theme import (
    BRAND,
    DIM,
    ERROR,
    HIGHLIGHT,
    TEXT,
    WARNING,
)

_SPARK_CHARS = frozenset("▁▂▃▄▅▆▇█░▒▓▌▍▎▏▐")
_SPARK_ORDER = "▁▂▃▄▅▆▇█"
_BAR_CHARS = frozenset("█▓▒░▄")
_FENCE_RE = re.compile(r"^```")
_TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
_ALIGN_RE = re.compile(r"(<==\s+aligns[^\n]*)", re.IGNORECASE)
_PERCENT_RE = re.compile(r"([+-]?\d+(?:\.\d+)?%)")
_ARROW_RE = re.compile(r"(→|->)")


def _is_sparkline(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 8:
        return False
    spark = sum(1 for ch in stripped if ch in _SPARK_CHARS)
    return spark >= 8 and spark * 2 >= len(stripped.replace(" ", ""))


def _is_bar_line(line: str) -> bool:
    bars = sum(1 for ch in line if ch in _BAR_CHARS)
    return bars >= 4 and "%" in line


def _is_table_row(line: str) -> bool:
    return bool(_TABLE_ROW_RE.match(line) or _TABLE_SEP_RE.match(line))


def _split_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def _spark_style(ch: str) -> str:
    if ch not in _SPARK_ORDER:
        return str(DIM)
    idx = _SPARK_ORDER.index(ch)
    if idx >= 6:
        return str(ERROR)
    if idx >= 4:
        return str(WARNING)
    if idx >= 2:
        return str(HIGHLIGHT)
    return str(BRAND)


def colorize_sparkline(line: str) -> Text:
    """Height-color a ▁▂▃▄▅▆▇█ run so a step-change is visible at a glance."""
    painted = Text()
    for ch in line:
        if ch in _SPARK_CHARS:
            painted.append(ch, style=_spark_style(ch if ch in _SPARK_ORDER else "▃"))
        else:
            painted.append(ch, style=str(DIM))
    return painted


def colorize_bar_line(line: str) -> Text:
    """Attribution row: label in body text, bar in warning/brand, percent dim."""
    painted = Text()
    in_bar = False
    for ch in line:
        if ch in _BAR_CHARS:
            in_bar = True
            painted.append(ch, style=str(WARNING))
            continue
        if in_bar and ch == " ":
            painted.append(ch)
            continue
        in_bar = False
        painted.append(ch, style=str(TEXT))
    return painted


def colorize_align_line(line: str) -> Text:
    """Deploy timeline row; highlight the ``<== aligns`` marker."""
    painted = Text()
    cursor = 0
    for match in _ALIGN_RE.finditer(line):
        painted.append(line[cursor : match.start()], style=str(DIM))
        painted.append(match.group(1), style=f"bold {HIGHLIGHT}")
        cursor = match.end()
    painted.append(line[cursor:], style=str(DIM))
    return painted


def colorize_step_line(line: str) -> Text:
    """Step-change callout: arrows and percents in highlight."""
    painted = Text(line, style=str(TEXT))
    for match in _ARROW_RE.finditer(line):
        painted.stylize(str(HIGHLIGHT), match.start(), match.end())
    for match in _PERCENT_RE.finditer(line):
        style = str(ERROR) if match.group(1).startswith("+") else str(BRAND)
        painted.stylize(style, match.start(), match.end())
    return painted


def markdown_table(lines: list[str]) -> Table | None:
    """Build a Rich table from GitHub-flavored markdown rows."""
    rows = [line for line in lines if line.strip()]
    if len(rows) < 2 or not _TABLE_SEP_RE.match(rows[1]):
        return None
    header = _split_row(rows[0])
    if not header:
        return None
    table = Table(
        box=SIMPLE,
        show_header=True,
        header_style=f"bold {HIGHLIGHT}",
        pad_edge=False,
        expand=False,
        border_style=str(DIM),
    )
    for title in header:
        table.add_column(title or " ")
    for raw in rows[2:]:
        cells = _split_row(raw)
        while len(cells) < len(header):
            cells.append("")
        styled: list[Text] = []
        for cell in cells[: len(header)]:
            lower = cell.lower()
            if "rejected" in lower:
                styled.append(Text(cell, style=str(DIM)))
            elif "supported" in lower or "aligns" in lower:
                styled.append(Text(cell, style=f"bold {BRAND}"))
            else:
                styled.append(Text(cell, style=str(TEXT)))
        table.add_row(*styled)
    return table


def _flush_markdown(chunks: list[str], out: list[tuple[str, str]]) -> None:
    body = "".join(chunks).strip("\n")
    chunks.clear()
    if body:
        out.append(("markdown", body))


def split_report_chunks(text: str) -> list[tuple[str, str]]:
    """Split ``text`` into ``(kind, body)`` chunks for mixed visual/markdown render."""
    lines = text.splitlines()
    chunks: list[tuple[str, str]] = []
    markdown: list[str] = []
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            markdown.append(line)
            index += 1
            continue
        if in_fence:
            markdown.append(line)
            index += 1
            continue
        if _is_table_row(line):
            _flush_markdown(markdown, chunks)
            table_lines = [line]
            index += 1
            while index < len(lines) and _is_table_row(lines[index]):
                table_lines.append(lines[index])
                index += 1
            chunks.append(("table", "\n".join(table_lines)))
            continue
        if _is_sparkline(line):
            _flush_markdown(markdown, chunks)
            chunks.append(("sparkline", line))
            index += 1
            continue
        if _is_bar_line(line):
            _flush_markdown(markdown, chunks)
            chunks.append(("bar", line))
            index += 1
            continue
        if _ALIGN_RE.search(line):
            _flush_markdown(markdown, chunks)
            chunks.append(("align", line))
            index += 1
            continue
        if _ARROW_RE.search(line) and _PERCENT_RE.search(line):
            _flush_markdown(markdown, chunks)
            chunks.append(("step", line))
            index += 1
            continue
        markdown.append(line)
        index += 1
    _flush_markdown(markdown, chunks)
    return chunks


def render_report_markdown(console: Console, text: str, *, build_markdown) -> None:
    """Render ``text``, painting visual rows and leaving prose to ``build_markdown``.

    ``build_markdown`` is the shared Markdown factory so tests can still
    substitute ``streaming.Markdown``.
    """
    import infrastructure.terminal.theme as ui_theme

    chunks = split_report_chunks(text)
    if not chunks:
        return
    if len(chunks) == 1 and chunks[0][0] == "markdown":
        with console.use_theme(ui_theme.MARKDOWN_THEME):
            console.print(build_markdown(chunks[0][1]))
        return
    for kind, body in chunks:
        if kind == "sparkline":
            console.print(colorize_sparkline(body))
        elif kind == "bar":
            console.print(colorize_bar_line(body))
        elif kind == "align":
            console.print(colorize_align_line(body))
        elif kind == "step":
            console.print(colorize_step_line(body))
        elif kind == "table":
            table = markdown_table(body.splitlines())
            if table is None:
                with console.use_theme(ui_theme.MARKDOWN_THEME):
                    console.print(build_markdown(body))
            else:
                console.print(table)
        else:
            with console.use_theme(ui_theme.MARKDOWN_THEME):
                console.print(build_markdown(body))


__all__ = [
    "colorize_align_line",
    "colorize_bar_line",
    "colorize_sparkline",
    "colorize_step_line",
    "markdown_table",
    "render_report_markdown",
    "split_report_chunks",
]
