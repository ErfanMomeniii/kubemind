"""LangGraph investigation agent.

Graph: planner → tool_caller → evaluator → (responder | tool_caller).
See docs/architecture.md §2.3 and docs/adr/0002-use-langgraph.md.
"""

import json
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from ai.llm import LLM
from ai.prompts import (
    EVALUATOR_SYSTEM,
    PLANNER_SYSTEM,
    RESPONDER_SYSTEM,
)
from ai.tools import ToolRegistry

MAX_ITERATIONS = 3


class AgentState(TypedDict, total=False):
    query: str
    cluster_id: str
    plan: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    confidence: str
    sufficient: bool
    next_calls: list[dict[str, Any]]
    answer: str
    root_cause: str | None
    proposed_action: dict[str, Any] | None
    iterations: int
    error: str | None


def build_agent(llm: LLM, tools: ToolRegistry) -> Any:
    """Compile the investigation graph. Returns a runnable graph."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", _planner_node(llm))
    graph.add_node("tool_caller", _tool_caller_node(tools))
    graph.add_node("evaluator", _evaluator_node(llm))
    graph.add_node("responder", _responder_node(llm))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "tool_caller")
    graph.add_edge("tool_caller", "evaluator")
    graph.add_conditional_edges(
        "evaluator",
        _after_evaluate,
        {"tool_caller": "tool_caller", "responder": "responder"},
    )
    graph.add_edge("responder", END)

    return graph.compile()


def _after_evaluate(state: AgentState) -> str:
    if state.get("error"):
        return "responder"
    if state.get("sufficient") is True:
        return "responder"
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        return "responder"
    return "tool_caller"


def _planner_node(llm: LLM):
    async def _run(state: AgentState) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": f"Question: {state['query']}"},
        ]
        try:
            raw = await llm.ainvoke(messages)
            parsed = _parse_json(raw)
        except Exception as exc:
            return {"plan": [], "error": f"planner failed: {exc}"}
        return {
            "plan": parsed.get("tool_calls", []),
            "iterations": 0,
            "tool_results": [],
            "evidence": [],
        }

    return _run


def _tool_caller_node(tools: ToolRegistry):
    async def _run(state: AgentState) -> dict[str, Any]:
        calls = state.get("plan") or state.get("next_calls") or []
        results: list[dict[str, Any]] = list(state.get("tool_results", []))
        evidence: list[dict[str, Any]] = list(state.get("evidence", []))

        for call in calls:
            tool_name = call.get("tool")
            tool_input = call.get("input", {})
            reason = call.get("reason", "")
            try:
                output = await tools.invoke(tool_name, tool_input)
            except Exception as exc:
                output = {"error": str(exc)}
            entry = {
                "tool": tool_name,
                "input": tool_input,
                "output": output,
                "reason": reason,
            }
            results.append(entry)
            evidence.append(entry)

        return {
            "tool_results": results,
            "evidence": evidence,
            "iterations": state.get("iterations", 0) + 1,
            "next_calls": [],
        }

    return _run


def _evaluator_node(llm: LLM):
    async def _run(state: AgentState) -> dict[str, Any]:
        if state.get("error"):
            return {"sufficient": True, "confidence": "low"}
        evidence_json = json.dumps(state.get("evidence", []), default=str)[:8000]
        messages = [
            {"role": "system", "content": EVALUATOR_SYSTEM},
            {
                "role": "user",
                "content": f"Evidence:\n{evidence_json}\n\nQuestion: {state['query']}",
            },
        ]
        try:
            raw = await llm.ainvoke(messages)
            parsed = _parse_json(raw)
        except Exception:
            return {"sufficient": True, "confidence": "low"}
        return {
            "sufficient": bool(parsed.get("sufficient", True)),
            "confidence": parsed.get("confidence", "low"),
            "next_calls": parsed.get("next_calls", []) or [],
        }

    return _run


def _responder_node(llm: LLM):
    async def _run(state: AgentState) -> dict[str, Any]:
        if state.get("error"):
            return {
                "answer": f"Investigation failed: {state['error']}",
                "confidence": "low",
                "root_cause": None,
                "proposed_action": None,
            }
        evidence_json = json.dumps(state.get("evidence", []), default=str)[:8000]
        messages = [
            {"role": "system", "content": RESPONDER_SYSTEM},
            {
                "role": "user",
                "content": f"Question: {state['query']}\n\nEvidence:\n{evidence_json}",
            },
        ]
        try:
            raw = await llm.ainvoke(messages)
        except Exception as exc:
            return {
                "answer": f"Responder failed: {exc}",
                "confidence": "low",
                "root_cause": None,
                "proposed_action": None,
            }
        parsed = _parse_json(raw)
        answer = parsed.get("answer") or raw.strip()
        return {
            "answer": answer,
            "confidence": parsed.get("confidence", "low"),
            "root_cause": parsed.get("root_cause"),
            "proposed_action": parsed.get("proposed_action"),
        }

    return _run


def _parse_json(raw: str) -> dict[str, Any]:
    """Parse JSON from LLM output, tolerating code fences, prose, single quotes."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
        else:
            text = text[3:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Fallback: single-quote dicts (some models emit Python-ish JSON)
    try:
        import ast

        return ast.literal_eval(candidate)
    except (ValueError, SyntaxError):
        return {}
