"""Kubernetes client (async wrapper around official kubernetes client).

The official `kubernetes` Python client is sync. We wrap blocking calls in
asyncio.to_thread to keep the event loop unblocked. See docs/architecture.md
§2.4 and docs/safety.md §10.
"""

import asyncio
from typing import Any

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

from integrations.base import BaseIntegrationClient, CircuitBreaker
from app.core.exceptions import IntegrationError
from app.core.logging import get_logger

log = get_logger()


class KubernetesClient(BaseIntegrationClient):
    """Async Kubernetes client.

    Auth via kubeconfig (local dev) or service account token (in-cluster / remote).
    """

    def __init__(
        self,
        server_url: str,
        *,
        token: str | None = None,
        kubeconfig_path: str | None = None,
        context: str | None = None,
        timeout: float | None = None,
    ) -> None:
        super().__init__(server_url, timeout=timeout)
        self._token = token
        self._kubeconfig_path = kubeconfig_path
        self._context = context
        self._api: k8s_client.CoreV1Api | None = None
        self._apps_api: k8s_client.AppsV1Api | None = None

    def _load(self) -> None:
        """Build k8s API clients. Called lazily on first use."""
        if self._api is not None:
            return

        if self._kubeconfig_path:
            k8s_config.load_kube_config(
                config_file=self._kubeconfig_path, context=self._context
            )
        elif self._token:
            configuration = k8s_client.Configuration()
            configuration.host = self.base_url
            configuration.api_key_prefix["authorization"] = "Bearer"
            configuration.api_key["authorization"] = self._token
            configuration.verify_ssl = True
            k8s_client.Configuration.set_default(configuration)
        else:
            try:
                k8s_config.load_incluster_config()
            except Exception as exc:
                raise IntegrationError(
                    "no k8s auth: provide token, kubeconfig, or run in-cluster"
                ) from exc

        self._api = k8s_client.CoreV1Api()
        self._apps_api = k8s_client.AppsV1Api()

    async def get_pods(self, namespace: str = "") -> list[dict[str, Any]]:
        async def _op() -> list[dict[str, Any]]:
            self._load()
            if namespace:
                resp = await asyncio.to_thread(self._api.list_namespaced_pod, namespace)  # type: ignore[union-attr]
            else:
                resp = await asyncio.to_thread(self._api.list_pod_for_all_namespaces)  # type: ignore[union-attr]
            return [_pod_summary(p) for p in resp.items]

        return await self._call(_op)

    async def get_events(self, namespace: str = "") -> list[dict[str, Any]]:
        async def _op() -> list[dict[str, Any]]:
            self._load()
            if namespace:
                resp = await asyncio.to_thread(self._api.list_namespaced_event, namespace)  # type: ignore[union-attr]
            else:
                resp = await asyncio.to_thread(self._api.list_event_for_all_namespaces)  # type: ignore[union-attr]
            return [_event_summary(e) for e in resp.items]

        return await self._call(_op)

    async def get_deployments(self, namespace: str = "") -> list[dict[str, Any]]:
        async def _op() -> list[dict[str, Any]]:
            self._load()
            if namespace:
                resp = await asyncio.to_thread(self._apps_api.list_namespaced_deployment, namespace)  # type: ignore[union-attr]
            else:
                resp = await asyncio.to_thread(self._apps_api.list_deployment_for_all_namespaces)  # type: ignore[union-attr]
            return [_deployment_summary(d) for d in resp.items]

        return await self._call(_op)

    async def get_deployment(self, namespace: str, name: str) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            self._load()
            resp = await asyncio.to_thread(
                self._apps_api.read_namespaced_deployment, name, namespace  # type: ignore[union-attr]
            )
            return _deployment_summary(resp)

        return await self._call(_op)

    async def get_logs(self, namespace: str, pod: str, tail_lines: int = 100) -> str:
        async def _op() -> str:
            self._load()
            return await asyncio.to_thread(
                self._api.read_namespaced_pod_log, pod, namespace, tail_lines=tail_lines  # type: ignore[union-attr]
            )

        return await self._call(_op)


def _pod_summary(p: Any) -> dict[str, Any]:
    restarts = sum(
        (cs.restart_count or 0) for cs in (p.status.container_statuses or [])
    )
    return {
        "name": p.metadata.name,
        "namespace": p.metadata.namespace,
        "phase": p.status.phase,
        "restarts": restarts,
        "ready": all(cs.ready for cs in (p.status.container_statuses or [])),
        "node": p.spec.node_name,
    }


def _event_summary(e: Any) -> dict[str, Any]:
    return {
        "name": e.metadata.name,
        "namespace": e.metadata.namespace,
        "type": e.type,
        "reason": e.reason,
        "message": e.message,
        "last_timestamp": e.last_timestamp.isoformat() if e.last_timestamp else None,
    }


def _deployment_summary(d: Any) -> dict[str, Any]:
    return {
        "name": d.metadata.name,
        "namespace": d.metadata.namespace,
        "replicas_desired": d.spec.replicas,
        "replicas_ready": d.status.ready_replicas or 0,
        "image": d.spec.template.spec.containers[0].image if d.spec.template.spec.containers else None,
        "available": d.status.available_replicas or 0,
    }
