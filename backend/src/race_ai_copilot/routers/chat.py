"""Chat endpoint.

Exposes ``POST /chat`` that accepts a ``ChatRequest`` and returns a
``ChatResponse`` produced by the ``ChatService`` orchestrator.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..models.schemas import ChatRequest, ChatResponse
from ..services.chat_service import ChatService

router = APIRouter(tags=["chat"])


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
) -> ChatResponse:
    """Process a chat message through the full reasoning pipeline.

    Args:
        request: The incoming chat message and metadata.

    Returns:
        A ``ChatResponse`` containing the generated answer, evidence,
        tool calls, and governance metadata.

    Responses:
        200: Success — the answer was generated.
    """
    return await service.answer(request)
