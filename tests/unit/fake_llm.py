"""FakeLLM for tests: returns canned JSON based on prompt content."""

from typing import Any

from ai.llm import LLM


PLANNER_RESPONSE = {
    "sub_questions": ["availability?", "recent events?"],
    "tool_calls": [
        {"tool": "query_prometheus", "input": {"promql": "avg_over_time(up[5m])"}, "reason": "availability"},
        {"tool": "get_events", "input": {"namespace": ""}, "reason": "recent events"},
    ],
}

EVALUATOR_SUFFICIENT = {
    "sufficient": True,
    "confidence": "high",
    "missing": [],
    "next_calls": [],
}

EVALUATOR_INSUFFICIENT = {
    "sufficient": False,
    "confidence": "low",
    "missing": ["pod logs"],
    "next_calls": [
        {"tool": "get_pods", "input": {"namespace": ""}, "reason": "pod health"}
    ],
}

RESPONDER_RESPONSE = {
    "answer": "Production is healthy. Availability 99.97%, no firing alerts, no recent critical events.",
    "confidence": "high",
    "root_cause": None,
    "proposed_action": None,
}


class FakeLLM(LLM):
    """Returns canned responses. Cycle through planner → evaluator → responder."""

    def __init__(
        self,
        planner: dict[str, Any] | None = None,
        evaluator: dict[str, Any] | None = None,
        responder: dict[str, Any] | None = None,
    ) -> None:
        import json

        self._planner = json.dumps(planner or PLANNER_RESPONSE)
        self._evaluator = json.dumps(evaluator or EVALUATOR_SUFFICIENT)
        self._responder = json.dumps(responder or RESPONDER_RESPONSE)
        self._call_count = 0

    async def ainvoke(self, messages: list[dict[str, str]]) -> str:
        content = messages[0]["content"]
        self._call_count += 1
        if "Decompose" in content or "tool plan" in content:
            return self._planner
        if "sufficient" in content.lower():
            return self._evaluator
        if "operations analyst" in content or "compose an answer" in content.lower():
            return self._responder
        return self._responder

    @property
    def model_name(self) -> str:
        return "fake-llm"
