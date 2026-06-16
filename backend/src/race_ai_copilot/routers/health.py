"""Health-check endpoint.

Provides a simple liveness probe that returns the current service status,
version, and timestamp.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..services.legacy_surface_service import LegacySurfaceService

router = APIRouter(tags=["health"])
_LEGACY_SURFACE_SERVICE = LegacySurfaceService()


@router.get("/health")
async def health_check():
    """Return service health status.

    Responses:
        200: Service is healthy and ready to accept requests.
    """
    settings = get_settings()
    return _LEGACY_SURFACE_SERVICE.build_health(settings.default_model)
