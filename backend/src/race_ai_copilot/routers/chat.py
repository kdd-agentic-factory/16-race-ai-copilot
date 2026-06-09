"""Chat endpoint.

Exposes ``POST /chat`` that accepts a ``ChatRequest`` and returns a
``ChatResponse`` produced by the ``ChatService`` orchestrator.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth_deps import Principal, get_current_principal
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
    principal: Annotated[Principal, Depends(get_current_principal)],
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
    return await service.answer(request, principal=principal)
