"""Kubernetes API client (async wrapper around official kubernetes client).

Stub: full implementation in Phase 2.
"""

from typing import Any


class KubernetesClient:
    """Async Kubernetes client.

    Methods (Phase 2):
    - get_pods(namespace)
    - get_events(namespace)
    - get_deployment(namespace, name)
    - get_logs(namespace, pod)
    - describe_resource(kind, namespace, name)
    - dry_run_apply(manifest)
    """

    def __init__(self, server_url: str, credential_ref: str) -> None:
        self.server_url = server_url
        self.credential_ref = credential_ref

    async def get_pods(self, namespace: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Phase 2")
