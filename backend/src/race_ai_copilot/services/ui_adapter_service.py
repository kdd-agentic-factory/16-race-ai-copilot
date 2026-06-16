"""Adapters for OpenWebUI and streaming/polling UX surfaces."""

from __future__ import annotations

from typing import Any

from ..contracts import RequestContext
from ..models.schemas import ChatRequest, ChatResponse
from ..models.ui import (
    OpenWebUIChatChoice,
    OpenWebUIChatChoiceMessage,
    OpenWebUIChatRequest,
    OpenWebUIChatResponse,
)


class UIAdapterService:
    """Translate canonical chat responses into UI-specific shapes."""

    def to_canonical_request(self, request: OpenWebUIChatRequest, context: RequestContext) -> ChatRequest:
        message = self._latest_user_message(request.messages)
        return ChatRequest(
            conversation_id=request.conversation_id,
            session_id=request.session_id,
            message=message,
            model=request.model,
            require_evidence=request.require_evidence,
            stream=request.stream,
            approval_granted=request.approval_granted,
            context={**request.context, "tenant_id": context.tenant_id},
        )

    def to_openwebui_response(self, response: ChatResponse, context: RequestContext, model: str | None = None) -> OpenWebUIChatResponse:
        return OpenWebUIChatResponse(
            id=response.conversation_id,
            model=model or "race-copilot",
            tenant_id=context.tenant_id,
            choices=[
                OpenWebUIChatChoice(
                    message=OpenWebUIChatChoiceMessage(content=response.answer),
                )
            ],
            context={
                "conversation_id": response.conversation_id,
                "message_id": response.message_id,
                "approval_required": response.approval_required,
            },
            usage={
                "prompt_tokens": len(response.answer.split()),
                "completion_tokens": len(response.answer.split()),
                "total_tokens": len(response.answer.split()) * 2,
            },
        )

    def stream_events(self, response: ChatResponse) -> list[str]:
        chunks = [line for line in response.answer.splitlines() if line.strip()]
        if not chunks:
            chunks = [response.answer]
        return [f"data: {chunk}\n\n" for chunk in chunks] + ["event: done\ndata: [DONE]\n\n"]

    def _latest_user_message(self, messages: list[Any]) -> str:
        for message in reversed(messages):
            if getattr(message, "role", None) == "user" or (isinstance(message, dict) and message.get("role") == "user"):
                return message.content if hasattr(message, "content") else message.get("content", "")
        return messages[-1].content if messages else ""
