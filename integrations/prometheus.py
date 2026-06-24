"""Prometheus client (PromQL queries via prometheus-api-client).

Stub: full implementation in Phase 2.
"""

from typing import Any


class PrometheusClient:
    """Async Prometheus client.

    Methods (Phase 2):
    - query(promql)
    - query_range(promql, start, end, step)
    - alerts()
    """

    def __init__(self, base_url: str, credential_ref: str | None = None) -> None:
        self.base_url = base_url
        self.credential_ref = credential_ref

    async def query(self, promql: str) -> dict[str, Any]:
        raise NotImplementedError("Phase 2")
