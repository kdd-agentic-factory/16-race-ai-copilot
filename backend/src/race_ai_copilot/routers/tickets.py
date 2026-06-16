"""Ticket triage and copilot endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth_deps import get_request_context
from ..contracts import RequestContext
from ..models.ticketing import SmartQueueRequest, SmartQueueResponse, TicketCopilotRequest, TicketCopilotResponse
from ..services.smart_queue_service import SmartQueueService
from ..services.ticket_copilot_service import TicketCopilotService

router = APIRouter(tags=["tickets"])

_DEFAULT_SMART_QUEUE_SERVICE = SmartQueueService()
_DEFAULT_TICKET_COPILOT_SERVICE = TicketCopilotService()


async def get_smart_queue_service() -> SmartQueueService:
    return _DEFAULT_SMART_QUEUE_SERVICE


async def get_ticket_copilot_service() -> TicketCopilotService:
    return _DEFAULT_TICKET_COPILOT_SERVICE


@router.post("/smart-queue", response_model=SmartQueueResponse)
@router.post("/tickets/smart-queue", response_model=SmartQueueResponse)
async def smart_queue(
    request: SmartQueueRequest,
    service: Annotated[SmartQueueService, Depends(get_smart_queue_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
) -> SmartQueueResponse:
    return service.rank(request, request_context=request_context)


@router.post("/ticket-copilot", response_model=TicketCopilotResponse)
@router.post("/tickets/copilot", response_model=TicketCopilotResponse)
async def ticket_copilot(
    request: TicketCopilotRequest,
    service: Annotated[TicketCopilotService, Depends(get_ticket_copilot_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
) -> TicketCopilotResponse:
    return service.summarize(request.ticket, queue_context=request.queue_snapshot, request_context=request_context)
