"""KubeMind investigation agent (LangGraph).

Stub: full graph implemented in Phase 2 (Incident Investigator module).
"""

from typing import TypedDict


class AgentState(TypedDict):
    query: str
    plan: list[str]
    tool_results: list[dict]
    confidence: str
    answer: str
    proposed_action: dict | None


def build_agent() -> None:
    """Build LangGraph agent graph.

    Phase 2: Planner → Tool Caller → Evaluator → Responder with conditional
    edge from Evaluator back to Tool Caller.
    """
    raise NotImplementedError("Agent graph built in Phase 2")
