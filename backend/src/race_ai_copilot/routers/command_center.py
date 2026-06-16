"""Command Center integration router."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth_deps import get_request_context
from ..contracts import CommandCenterRequestEnvelope, CommandCenterResponseEnvelope, RequestContext
from ..services.command_center_service import CommandCenterService

router = APIRouter(tags=["command-center"])

_DEFAULT_COMMAND_CENTER_SERVICE = CommandCenterService()


async def get_command_center_service() -> CommandCenterService:
    return _DEFAULT_COMMAND_CENTER_SERVICE


@router.post("/chat", response_model=CommandCenterResponseEnvelope)
async def command_center_chat(
    request: CommandCenterRequestEnvelope,
    service: Annotated[CommandCenterService, Depends(get_command_center_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
) -> CommandCenterResponseEnvelope:
    if request.context.request_id is None:
        request = request.model_copy(update={"context": request_context})
    return await asyncio.to_thread(service.route, request)
