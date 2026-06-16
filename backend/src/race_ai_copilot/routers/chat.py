"""Chat endpoint.

Exposes ``POST /chat`` that accepts a ``ChatRequest`` and returns a
``ChatResponse`` produced by the ``ChatService`` orchestrator.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..auth_deps import Principal, get_current_principal, get_request_context
from ..contracts import RequestContext
from ..models.schemas import ChatRequest, ChatResponse
from ..services.chat_service import ChatService
from ..services.ui_adapter_service import UIAdapterService

router = APIRouter(tags=["chat"])
_UI_ADAPTER_SERVICE = UIAdapterService()


async def get_chat_service() -> ChatService:
    """Dependency provider — injected by ``main.py`` via ``app.state``.

    This function is overridden at startup with the actual singleton
    instance.  See ``main.py`` for the wiring.
    """
    # The override in main.py replaces this with the real service.
    raise RuntimeError("ChatService not initialised — call override_dependency first.")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
) -> ChatResponse:
    """Process a chat message through the full reasoning pipeline.

    Args:
        request: The incoming chat message and metadata.
        principal: The authenticated caller resolved from JWT / trusted headers.

    Returns:
        A ``ChatResponse`` containing the generated answer, evidence,
        tool calls, and governance metadata.

    Responses:
        200: Success — the answer was generated.
        403: The caller lacks the required role to grant approval.
    """
    return await service.answer(request, principal=principal, request_context=request_context)


@router.post("/chat/poll", response_model=ChatResponse)
async def chat_poll(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
) -> ChatResponse:
    return await service.answer(request, principal=principal, request_context=request_context)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
):
    response = await service.answer(request, principal=principal, request_context=request_context)

    async def _events():
        for event in _UI_ADAPTER_SERVICE.stream_events(response):
            yield event
            await asyncio.sleep(0)

    return StreamingResponse(_events(), media_type="text/event-stream")
