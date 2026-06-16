"""Canonical ticketing models for the Smart Queue and Copilot layer."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class LifecycleState(str, Enum):
    new = "new"
    in_progress = "in_progress"
    waiting_customer = "waiting_customer"
    waiting_third_party = "waiting_third_party"
    resolved = "resolved"
    closed = "closed"


class SlaStatus(str, Enum):
    healthy = "healthy"
    at_risk = "at_risk"
    breached = "breached"
    paused = "paused"


class TicketInput(BaseModel):
    ticket_id: str
    subject: str
    description: str = ""
    queue: str = "general"
    tenant_id: str | None = None
    severity: SeverityLevel = SeverityLevel.medium
    age_hours: int = Field(default=0, ge=0)
    lifecycle_state: LifecycleState = LifecycleState.new
    sla_remaining_minutes: int | None = None
    customer_tier: str = "standard"
    tags: list[str] = Field(default_factory=list)
    blocked: bool = False
    assignee: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmartQueueRequest(BaseModel):
    tickets: list[TicketInput] = Field(default_factory=list)
    queue_name: str | None = None
    max_items: int | None = Field(default=None, ge=1)


class RankedTicket(BaseModel):
    ticket: TicketInput
    rank: int
    score: float
    band: str
    sla_status: SlaStatus
    reasons: list[str] = Field(default_factory=list)
    recommended_action: str


class SmartQueueResponse(BaseModel):
    queue_name: str | None = None
    ranked_tickets: list[RankedTicket] = Field(default_factory=list)
    summary: str
    total_tickets: int
    active_tickets: int


class TicketCopilotRequest(BaseModel):
    ticket: TicketInput
    queue_snapshot: list[TicketInput] = Field(default_factory=list)


class TicketCopilotResponse(BaseModel):
    ticket_id: str
    summary: str
    similar_case_hints: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    escalation_hints: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.72, ge=0.0, le=1.0)
    queue_band: str
    sla_status: SlaStatus
