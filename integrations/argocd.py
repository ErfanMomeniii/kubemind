"""ArgoCD client (REST API).

Stub: full implementation in Phase 2.
"""

from typing import Any


class ArgoCDClient:
    """Async ArgoCD client.

    Methods (Phase 2):
    - list_apps()
    - get_app(name)
    - sync_status(name)
    - rollout_history(name)
    """

    def __init__(self, base_url: str, credential_ref: str) -> None:
        self.base_url = base_url
        self.credential_ref = credential_ref

    async def list_apps(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Phase 2")
