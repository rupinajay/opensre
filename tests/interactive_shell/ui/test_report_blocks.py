"""Structured rich-output primitives render scannable, theme-graded blocks."""

from __future__ import annotations

import io

from rich.console import Console

from infrastructure.terminal.theme import ERROR, SECONDARY
from surfaces.interactive_shell.ui.report_blocks import (
    bar_chart,
    comparison_table,
    panel,
    sparkline,
)


def _render(renderable: object) -> str:
    # Arrange: a plain (no-ANSI) console so assertions read the visible text.
    buf = io.StringIO()
    Console(file=buf, force_terminal=False, highlight=False, width=80).print(renderable)
    return buf.getvalue()


def test_sparkline_is_empty_for_no_values() -> None:
    assert sparkline([]) == ""


def test_sparkline_scales_min_to_max_across_the_glyph_ramp() -> None:
    # Act: an ascending series should climb from the lowest to the highest glyph.
    line = sparkline([0, 1, 2, 3, 4, 5, 6, 7])

    # Assert: first tick is the floor glyph, last is the ceiling glyph.
    assert line[0] == "▁"
    assert line[-1] == "█"
    assert len(line) == 8


def test_sparkline_flat_series_uses_the_mid_glyph() -> None:
    assert sparkline([5, 5, 5]) == "▅▅▅"


def test_bar_chart_scales_bars_to_the_largest_magnitude() -> None:
    # Act
    chart = bar_chart([("db", 76), ("pool_wait", 47), ("app", 1)], width=20, unit="ms")
    text = chart.plain

    # Assert: the peak row is the widest bar; every label and signed value shows.
    db_bar = text.splitlines()[0].count("█")
    app_bar = text.splitlines()[2].count("█")
    assert db_bar > app_bar
    assert "db" in text and "+76ms" in text
    assert "app" in text and "+1ms" in text


def test_bar_chart_grades_the_dominant_row_as_the_alert_colour() -> None:
    # Act: db is 60%+ of the total, app is a rounding error.
    chart = bar_chart([("db", 76), ("app", 1)], width=20)

    # Assert: the dominant bar carries the ERROR style, the tiny one does not.
    bar_styles = {span.style for span in chart.spans if "█" in chart.plain[span.start : span.end]}
    assert str(ERROR) in bar_styles
    assert str(SECONDARY) in bar_styles


def test_bar_chart_shows_a_bar_for_negative_contributors() -> None:
    # Assert: a negative value still draws a bar and keeps its sign in the label.
    chart = bar_chart([("db", 76), ("inventory", -2)], width=20)
    inventory_line = chart.plain.splitlines()[1]
    assert "█" in inventory_line
    assert "-2" in inventory_line


def test_comparison_table_shows_headers_and_every_row() -> None:
    out = _render(
        comparison_table(
            ("Hypothesis", "Verdict"),
            [("Traffic growth", "rejected"), ("Cache hit drop", "rejected")],
            title="Alternatives",
        )
    )
    assert "Hypothesis" in out and "Verdict" in out
    assert "Traffic growth" in out and "Cache hit drop" in out
    assert "Alternatives" in out


def test_panel_frames_the_body_under_its_title() -> None:
    out = _render(panel(bar_chart([("db", 76)], width=10), title="Where the time went"))
    assert "Where the time went" in out
    assert "db" in out
    # A rounded border box is drawn around the content.
    assert "╭" in out and "╰" in out
