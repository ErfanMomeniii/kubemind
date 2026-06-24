"""Prometheus client (async, httpx).

Queries Prometheus HTTP API. See docs/architecture.md §2.4.
"""

from typing import Any

import httpx

from integrations.base import BaseIntegrationClient


class PrometheusClient(BaseIntegrationClient):
    """Async Prometheus client.

    Methods:
    - query(promql, time?) → instant query
    - query_range(promql, start, end, step) → range query
    - alerts() → firing alerts
    """

    def __init__(
        self,
        base_url: str,
        *,
        credential_ref: str | None = None,
        timeout: float | None = None,
    ) -> None:
        super().__init__(base_url, credential_ref=credential_ref, timeout=timeout)

    async def query(self, promql: str, time: float | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"query": promql}
        if time is not None:
            params["time"] = time

        async def _op() -> dict[str, Any]:
            client = await self._http()
            resp = await client.get("/api/v1/query", params=params)
            resp.raise_for_status()
            return resp.json()

        return await self._call(_op)

    async def query_range(
        self, promql: str, start: float, end: float, step: str
    ) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            client = await self._http()
            resp = await client.get(
                "/api/v1/query_range",
                params={"query": promql, "start": start, "end": end, "step": step},
            )
            resp.raise_for_status()
            return resp.json()

        return await self._call(_op)

    async def alerts(self) -> dict[str, Any]:
        async def _op() -> dict[str, Any]:
            client = await self._http()
            resp = await client.get("/api/v1/alerts")
            resp.raise_for_status()
            return resp.json()

        return await self._call(_op)

    async def up_ratio(self, cluster: str, window: str = "5m") -> float:
        """Fraction of up targets for a cluster over window. 0.0–1.0."""
        result = await self.query(f'avg_over_time(up{{cluster="{cluster}"}}[{window}])')
        value = _extract_scalar(result)
        return float(value) if value is not None else 0.0

    async def error_rate(self, window: str = "5m") -> float:
        """5xx / total request ratio over window."""
        promql = (
            'sum(rate(http_requests_total{status=~"5.."}[' + window + "]))"
            " / sum(rate(http_requests_total[" + window + "]))"
        )
        result = await self.query(promql)
        value = _extract_scalar(result)
        return float(value) if value is not None else 0.0

    async def firing_critical_alerts(self) -> list[dict[str, Any]]:
        data = await self.alerts()
        return [
            a
            for a in data.get("data", {}).get("alerts", [])
            if a.get("state") == "firing"
            and a.get("labels", {}).get("severity") == "critical"
        ]


def _extract_scalar(response: dict[str, Any]) -> str | None:
    """Pull a scalar value from a Prometheus instant query response."""
    result = response.get("data", {}).get("result", [])
    if not result:
        return None
    first = result[0]
    value = first.get("value")
    if isinstance(value, list) and len(value) >= 2:
        return value[1]
    return None
