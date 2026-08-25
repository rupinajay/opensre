"""Inner ReAct goal reviewer uses closed structured verdicts."""

from __future__ import annotations

from typing import Any

from core.agent.goals import GoalObservation
from core.agent_harness.turns.goal_review import build_goal_reviewer
from core.llm.types import AgentLLMResponse


class _ScriptedLLM:
    model_id = "test"

    def __init__(self, content: str) -> None:
        self.content = content
        self.invokes = 0

    def tool_schemas(self, tools: list[Any]) -> list[dict[str, Any]]:
        _ = tools
        return []

    def invoke(
        self,
        messages: list[dict[str, Any]],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentLLMResponse:
        _ = (messages, system, tools)
        self.invokes += 1
        return AgentLLMResponse(content=self.content)


def _obs(*, text: str = "done", evidence: int = 1) -> GoalObservation:
    return GoalObservation(
        final_text=text,
        evidence_count=evidence,
        iteration=1,
        max_iterations=4,
    )


def test_goal_reviewer_rejects_on_structured_not_reached() -> None:
    llm = _ScriptedLLM('{"verdict": "NOT_REACHED"}')
    goal = build_goal_reviewer(llm, "delete the cron", executed_tool_names=["shell_run"])
    assert goal.verify is not None
    assert goal.verify(_obs()) is False
    assert llm.invokes == 1


def test_goal_reviewer_accepts_on_structured_reached() -> None:
    llm = _ScriptedLLM('{"verdict": "GOAL_REACHED"}')
    goal = build_goal_reviewer(llm, "delete the cron", executed_tool_names=["shell_run"])
    assert goal.verify is not None
    assert goal.verify(_obs()) is True


def test_goal_reviewer_fails_open_on_free_text() -> None:
    """Prose without JSON must accept (fail open) — never force extra ReAct work."""
    llm = _ScriptedLLM("NOT_REACHED — keep going")
    goal = build_goal_reviewer(llm, "delete the cron", executed_tool_names=["shell_run"])
    assert goal.verify is not None
    assert goal.verify(_obs()) is True


def test_goal_reviewer_rejects_idle_after_ask_user_answers() -> None:
    from core.agent.goals import should_accept_with_goal
    from core.agent_harness.session.pending_choice import (
        AskUserQuestion,
        format_ask_user_answers,
    )

    answers = format_ask_user_answers(
        (
            AskUserQuestion(label="Env", title="Where is it?", options=("Prod", "Dev")),
            AskUserQuestion(label="Window", title="What window?", options=("24h", "7d")),
        ),
        ("Dev", "24h"),
    )
    llm = _ScriptedLLM('{"verdict": "GOAL_REACHED"}')
    names: list[str] = []
    goal = build_goal_reviewer(llm, answers, executed_tool_names=names)
    assert goal.verify is not None
    assert goal.verify(_obs(text="I'll wait.", evidence=0)) is False
    assert llm.invokes == 0
    accept, nudge = should_accept_with_goal(
        goal,
        final_text="I'll wait.",
        evidence_count=0,
        iteration=0,
        max_iterations=8,
    )
    assert accept is False
    assert nudge is not None
    assert "go-ahead" in nudge
