"""Models for OpenWebUI and UI adapter responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class OpenWebUIMessage(BaseModel):
    role: str
    content: str


class OpenWebUIChatRequest(BaseModel):
    model: str | None = None
    messages: list[OpenWebUIMessage] = Field(default_factory=list)
    stream: bool = False
    conversation_id: str | None = None
    session_id: str | None = None
    require_evidence: bool = True
    approval_granted: bool = False
    context: dict[str, Any] = Field(default_factory=dict)


class OpenWebUIChatChoiceMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class OpenWebUIChatChoice(BaseModel):
    index: int = 0
    message: OpenWebUIChatChoiceMessage
    finish_reason: str = "stop"


class OpenWebUIChatResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp()))
    model: str = "race-copilot"
    tenant_id: str
    choices: list[OpenWebUIChatChoice] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
