"""Unit test: agent graph runs end-to-end with FakeLLM + mocked tools."""

from unittest.mock import AsyncMock

import pytest

from ai.agent import build_agent
from ai.tools import ToolRegistry
from integrations.k8s import KubernetesClient
from integrations.prometheus import PrometheusClient
from tests.unit.fake_llm import FakeLLM


def _build_tools() -> ToolRegistry:
    prom = AsyncMock(spec=PrometheusClient)
    prom.query = AsyncMock(return_value={"data": {"result": [{"value": ["0", "0.9997"]}]}})

    k8s = AsyncMock(spec=KubernetesClient)
    k8s.get_pods = AsyncMock(return_value=[])
    k8s.get_events = AsyncMock(return_value=[{"type": "Normal", "reason": "Started"}])
    k8s.get_deployments = AsyncMock(return_value=[])
    k8s.get_deployment = AsyncMock(return_value={})
    k8s.get_logs = AsyncMock(return_value="")

    return ToolRegistry(prometheus=prom, k8s=k8s)


async def test_agent_runs_and_responds():
    llm = FakeLLM()
    tools = _build_tools()
    agent = build_agent(llm, tools)

    result = await agent.ainvoke({"query": "Is production healthy?", "cluster_id": "c1"})

    assert result["answer"]
    assert result["confidence"] == "high"
    assert len(result["evidence"]) >= 2
    assert result["iterations"] >= 1


async def test_agent_loops_when_evidence_insufficient():
    import json

    llm = FakeLLM(evaluator=json.dumps({
        "sufficient": False,
        "confidence": "low",
        "missing": ["pods"],
        "next_calls": [{"tool": "get_pods", "input": {"namespace": ""}, "reason": "pod health"}],
    }))
    tools = _build_tools()
    agent = build_agent(llm, tools)

    result = await agent.ainvoke({"query": "Why is the API slow?", "cluster_id": "c1"})

    # Should have looped at least once (initial plan + next_calls)
    assert len(result["evidence"]) >= 3
    assert result["iterations"] >= 2


async def test_agent_handles_planner_error():
    llm = FakeLLM(planner={"sub_questions": [], "tool_calls": []})
    tools = _build_tools()
    agent = build_agent(llm, tools)

    result = await agent.ainvoke({"query": "test", "cluster_id": "c1"})

    # No tool calls planned → still reaches responder
    assert "answer" in result


async def test_agent_capped_at_max_iterations():
    import json

    # Evaluator always says insufficient — agent must stop at MAX_ITERATIONS (3)
    llm = FakeLLM(evaluator=json.dumps({
        "sufficient": False,
        "confidence": "low",
        "missing": ["more"],
        "next_calls": [{"tool": "get_pods", "input": {}, "reason": "again"}],
    }))
    tools = _build_tools()
    agent = build_agent(llm, tools)

    result = await agent.ainvoke({"query": "test", "cluster_id": "c1"})

    assert result["iterations"] <= 3
