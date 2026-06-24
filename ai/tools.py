"""Agent tools: wrap integration clients into a registry the agent can invoke.

Each tool: name, description, input schema, async invoke(). The planner
references these by name; the tool_caller dispatches via ToolRegistry.invoke.
"""

from typing import Any, Protocol

from integrations.k8s import KubernetesClient
from integrations.prometheus import PrometheusClient
from app.core.exceptions import IntegrationError
from app.core.logging import get_logger

log = get_logger()


class Tool(Protocol):
    name: str
    description: str

    async def invoke(self, input: dict[str, Any]) -> Any: ...


class QueryPrometheus:
    name = "query_prometheus"
    description = "Run a PromQL instant query against Prometheus."

    def __init__(self, client: PrometheusClient) -> None:
        self._client = client

    async def invoke(self, input: dict[str, Any]) -> Any:
        promql = input.get("promql")
        if not promql:
            raise IntegrationError("query_prometheus requires 'promql'")
        return await self._client.query(promql)


class GetPods:
    name = "get_pods"
    description = "List pods, optionally filtered to a namespace."

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    async def invoke(self, input: dict[str, Any]) -> Any:
        return await self._client.get_pods(namespace=input.get("namespace", ""))


class GetEvents:
    name = "get_events"
    description = "List Kubernetes events, optionally filtered to a namespace."

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    async def invoke(self, input: dict[str, Any]) -> Any:
        return await self._client.get_events(namespace=input.get("namespace", ""))


class GetDeployments:
    name = "get_deployments"
    description = "List deployments, optionally filtered to a namespace."

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    async def invoke(self, input: dict[str, Any]) -> Any:
        return await self._client.get_deployments(namespace=input.get("namespace", ""))


class GetDeployment:
    name = "get_deployment"
    description = "Read a single deployment by namespace + name."

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    async def invoke(self, input: dict[str, Any]) -> Any:
        namespace = input.get("namespace")
        name = input.get("name")
        if not namespace or not name:
            raise IntegrationError("get_deployment requires 'namespace' and 'name'")
        return await self._client.get_deployment(namespace, name)


class GetLogs:
    name = "get_logs"
    description = "Fetch recent logs for a pod."

    def __init__(self, client: KubernetesClient) -> None:
        self._client = client

    async def invoke(self, input: dict[str, Any]) -> Any:
        namespace = input.get("namespace")
        pod = input.get("pod")
        if not namespace or not pod:
            raise IntegrationError("get_logs requires 'namespace' and 'pod'")
        tail = int(input.get("tail_lines", 100))
        return await self._client.get_logs(namespace, pod, tail_lines=tail)


class ToolRegistry:
    """Holds tools, dispatches by name. Built from integration clients."""

    def __init__(self, prometheus: PrometheusClient, k8s: KubernetesClient) -> None:
        self._tools: dict[str, Tool] = {
            "query_prometheus": QueryPrometheus(prometheus),
            "get_pods": GetPods(k8s),
            "get_events": GetEvents(k8s),
            "get_deployments": GetDeployments(k8s),
            "get_deployment": GetDeployment(k8s),
            "get_logs": GetLogs(k8s),
        }

    async def invoke(self, name: str, input: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise IntegrationError(f"unknown tool: {name}")
        log.info("tool_invoke", tool=name, input_keys=list(input.keys()))
        try:
            return await tool.invoke(input)
        except IntegrationError:
            raise
        except Exception as exc:
            raise IntegrationError(f"tool {name} failed: {exc}") from exc

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())
