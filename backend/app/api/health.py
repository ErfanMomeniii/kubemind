"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    """Readiness probe — checks DB + Redis connectivity.

    MVP: returns ok. Full implementation checks integrations in ADR-0009.
    """
    return {"status": "ok"}
