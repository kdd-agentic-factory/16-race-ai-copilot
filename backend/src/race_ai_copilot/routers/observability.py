"""Reporting and observability endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ..auth_deps import get_request_context
from ..contracts import RequestContext
from ..services.observability_service import ObservabilityService

router = APIRouter(tags=["observability"])
_DEFAULT_OBSERVABILITY_SERVICE = ObservabilityService()


async def get_observability_service() -> ObservabilityService:
    return _DEFAULT_OBSERVABILITY_SERVICE


@router.post("/observability/sla-health")
async def sla_health(
    request: dict[str, Any],
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
):
    return service.sla_health(request.get("tickets", []), context=request_context)


@router.post("/observability/groundedness")
async def groundedness(
    request: dict[str, Any],
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
):
    return service.groundedness(request.get("answer", ""), request.get("evidence", []), context=request_context)


@router.post("/observability/approvals")
async def approvals(
    request: dict[str, Any],
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
):
    return service.approvals(request.get("approvals", []), context=request_context)


@router.post("/observability/improvement-signals")
async def improvement_signals(
    request: dict[str, Any],
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
):
    return service.improvement_signals(
        sla_health=request.get("sla_health", {}),
        groundedness=request.get("groundedness", {}),
        approvals=request.get("approvals", {}),
        context=request_context,
    )
