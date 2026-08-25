"""Rich rendering primitives for structured agent output.

Panels, horizontal bar charts, sparklines, and comparison tables the
interactive shell composes for metric summaries, attribution breakdowns, and
hypothesis comparisons — so structured content is scannable instead of a flat
markdown block. Every builder returns a Rich renderable; callers print it, and
tests capture it through a ``Console(file=StringIO)``.
"""

from __future__ import annotations

from collections.abc import Sequence

from rich import box
from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from infrastructure.terminal.theme import (
    BRAND,
    DIM,
    ERROR,
    HIGHLIGHT,
    SECONDARY,
    TEXT,
    WARNING,
)

#: Eight block glyphs from lowest to highest, for inline sparklines.
_SPARK_TICKS = "▁▂▃▄▅▆▇█"
_BAR_GLYPH = "█"
_DEFAULT_BAR_WIDTH = 28


def sparkline(values: Sequence[float]) -> str:
    """Return an inline block-glyph sparkline for ``values`` (min→max scaled).

    A flat or single-point series maps to the mid glyph; an empty series is "".
    """
    if not values:
        return ""
    low = min(values)
    high = max(values)
    span = high - low
    if span == 0:
        return _SPARK_TICKS[len(_SPARK_TICKS) // 2] * len(values)
    last = len(_SPARK_TICKS) - 1
    return "".join(_SPARK_TICKS[round((value - low) / span * last)] for value in values)


def _bar_style(fraction: float) -> str:
    """Grade a bar by its share of the largest value: high→red, mid→amber, low→calm."""
    if fraction >= 0.5:
        return str(ERROR)
    if fraction >= 0.25:
        return str(WARNING)
    return str(SECONDARY)


def bar_chart(
    rows: Sequence[tuple[str, float]],
    *,
    width: int = _DEFAULT_BAR_WIDTH,
    unit: str = "",
) -> Text:
    """Horizontal bar chart: ``(label, value)`` rows scaled to the largest magnitude.

    Bars are sized by absolute value so negative contributors still show; the
    printed value keeps its sign. Each row is coloured by its share of the peak.
    """
    body = Text()
    if not rows:
        return body
    peak = max(abs(value) for _label, value in rows) or 1.0
    label_width = max(len(label) for label, _value in rows)
    for index, (label, value) in enumerate(rows):
        fraction = abs(value) / peak
        filled = max(1, round(fraction * width)) if value else 0
        share = f"{value:+g}{unit}".rjust(8)
        body.append(f"{label.ljust(label_width)}  ", style=str(TEXT))
        body.append(_BAR_GLYPH * filled, style=_bar_style(fraction))
        body.append(f" {share}", style=str(DIM))
        if index != len(rows) - 1:
            body.append("\n")
    return body


def comparison_table(
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    title: str | None = None,
) -> Table:
    """Aligned table with a header rule: bright headers, dim body, first column highlighted."""
    table = Table(
        box=box.SIMPLE_HEAD,
        title=title,
        title_style=str(SECONDARY),
        header_style=str(HIGHLIGHT),
        border_style=str(DIM),
        pad_edge=False,
        expand=False,
    )
    for position, name in enumerate(columns):
        table.add_column(name, style=str(BRAND) if position == 0 else str(DIM))
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    return table


def panel(body: RenderableType, *, title: str) -> Panel:
    """Wrap ``body`` in a titled, dim-bordered panel for a grouped section."""
    return Panel(
        body,
        title=Text(title, style=str(HIGHLIGHT)),
        title_align="left",
        border_style=str(DIM),
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )


__all__ = [
    "bar_chart",
    "comparison_table",
    "panel",
    "sparkline",
]
