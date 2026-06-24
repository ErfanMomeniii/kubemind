"""API route definitions."""

from fastapi import APIRouter

from app.api import (
    architecture,
    auth,
    clusters,
    dashboard,
    deployments,
    health,
    query,
    sync,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(clusters.router)
api_router.include_router(dashboard.router)
api_router.include_router(query.router)
api_router.include_router(sync.router)
api_router.include_router(deployments.router)
api_router.include_router(architecture.router)
