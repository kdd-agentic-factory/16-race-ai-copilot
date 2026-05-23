"""Health-check endpoint.

Provides a simple liveness probe that returns the current service status,
version, and timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Return service health status.

    Responses:
        200: Service is healthy and ready to accept requests.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
