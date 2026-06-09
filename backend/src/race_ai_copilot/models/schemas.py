"""Pydantic schemas for the Race AI Copilot API.

Defines the request/response models used by the chat endpoint as well as
internal data structures for tool traces, evidence, and recommendations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# Internal / supporting models
# ──────────────────────────────────────────────────────────────────────

class ToolCallRecord(BaseModel):
    """Records a specific tool execution and its result."""

    tool_name: str = Field(..., description="The name of the tool being called")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters passed to the tool"
    )
    result: Optional[Any] = Field(
        None, description="The output returned by the tool"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Time of execution"
    )


class EvidenceItem(BaseModel):
    """A single piece of grounding evidence from a source."""

    id: str = Field(..., description="Unique identifier for the evidence source")
    title: str = Field(..., description="Title of the document or data source")
    url_or_path: str = Field(
        ..., description="Location of the source (URL or file path)"
    )
    snippet: str = Field(
        ..., description="The specific text snippet used for grounding"
    )


class EvidencePacket(BaseModel):
    """A collection of evidence used to ground a response."""

    sources: List[EvidenceItem] = Field(
        default_factory=list, description="List of cited sources"
    )
    raw_data: List[str] = Field(
        default_factory=list, description="The raw data retrieved from tools/RAG"
    )
    groundedness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ratio of evidential claims vs total claims",
    )


class Recommendation(BaseModel):
    """A structured recommendation produced by the copilot."""

    action: str = Field(..., description="The recommended action")
    rationale: str = Field(
        ..., description="Why this action is recommended"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the action"
    )


# ──────────────────────────────────────────────────────────────────────
# API models
# ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request object for the chat endpoint."""

    conversation_id: Optional[str] = Field(
        None,
        description="Existing conversation ID for follow-up messages. "
        "If omitted a new conversation is started.",
    )
    session_id: Optional[str] = Field(
        None,
        description="Session identifier for grouping conversations "
        "(e.g. 'fp1-jerez-demo').",
    )
    message: str = Field(
        ..., min_length=1, description="The user's input message"
    )
    model: Optional[str] = Field(
        None,
        description="Override the default LLM model for this request.",
    )
    require_evidence: bool = Field(
        default=True,
        description="When True the response MUST be grounded in evidence.",
    )
    stream: bool = Field(
        default=False,
        description="When True the response is streamed token-by-token.",
    )
    approval_granted: bool = Field(
        default=False,
        description="When True, the user (e.g. crew chief) has explicitly granted "
        "approval for critical actions. Tools that require approval will only "
        "execute when this flag is True.",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context such as circuit_id, session_type, etc.",
    )


class ChatResponse(BaseModel):
    """Response object for the chat endpoint."""

    conversation_id: str = Field(
        ..., description="Unique conversation identifier"
    )
    message_id: str = Field(
        ..., description="Unique message identifier within the conversation"
    )
    answer: str = Field(
        ..., description="The generated response text (already sanitized)"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the generated answer",
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="List of evidence sources used to ground the answer",
    )
    tool_calls: List[ToolCallRecord] = Field(
        default_factory=list,
        description="Sequence of tool calls executed during reasoning",
    )
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="Structured recommendations extracted from the answer",
    )
    approval_required: bool = Field(
        default=False,
        description="Whether crew chief approval is needed before acting",
    )
    approver_role: Optional[str] = Field(
        None,
        description="The role responsible for approval (e.g. 'crew_chief')",
    )
    uncertainty: Optional[str] = Field(
        None,
        description="Description of uncertainty or limitations in the answer",
    )
    next_actions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up actions the user can take",
    )
