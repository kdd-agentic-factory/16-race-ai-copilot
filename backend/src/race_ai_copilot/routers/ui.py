"""UX integration adapters for OpenWebUI and command-center clients."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..auth_deps import Principal, get_current_principal, get_request_context
from ..contracts import RequestContext
from ..models.ui import OpenWebUIChatRequest, OpenWebUIChatResponse
from ..services.chat_service import ChatService
from ..services.ui_adapter_service import UIAdapterService
from .chat import get_chat_service

router = APIRouter(tags=["ui-adapters"])
_UI_ADAPTER_SERVICE = UIAdapterService()


@router.post("/integrations/openwebui/chat", response_model=OpenWebUIChatResponse)
async def openwebui_chat(
    request: OpenWebUIChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
) -> OpenWebUIChatResponse:
    canonical_request = _UI_ADAPTER_SERVICE.to_canonical_request(request, request_context)
    response = await service.answer(canonical_request, principal=principal, request_context=request_context)
    return _UI_ADAPTER_SERVICE.to_openwebui_response(response, context=request_context, model=request.model)


@router.post("/integrations/openwebui/chat/stream")
async def openwebui_chat_stream(
    request: OpenWebUIChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
):
    canonical_request = _UI_ADAPTER_SERVICE.to_canonical_request(request, request_context)
    response = await service.answer(canonical_request, principal=principal, request_context=request_context)

    async def _events():
        for event in _UI_ADAPTER_SERVICE.stream_events(response):
            yield event
            await asyncio.sleep(0)

    return StreamingResponse(_events(), media_type="text/event-stream")
