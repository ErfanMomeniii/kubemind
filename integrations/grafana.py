"""Grafana client (REST API).

Stub: full implementation in Phase 2.
"""

from typing import Any


class GrafanaClient:
    """Async Grafana client.

    Methods (Phase 2):
    - get_dashboard(uid)
    - snapshot(dashboard, expires)
    """

    def __init__(self, base_url: str, credential_ref: str) -> None:
        self.base_url = base_url
        self.credential_ref = credential_ref

    async def get_dashboard(self, uid: str) -> dict[str, Any]:
        raise NotImplementedError("Phase 2")
