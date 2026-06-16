"""Legacy prototype contracts preserved for compatibility routes.

These models mirror the original ``services/copilot-api/app`` payloads so the
canonical backend can absorb the old surface without breaking clients that
still rely on the prototype request/response shapes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    telemetry = "telemetry"
    document = "document"
    session = "session"
    model = "model"
    pattern = "pattern"


class ToolStatus(str, Enum):
    proposed = "proposed"
    executed = "executed"
    blocked = "blocked"


class RecommendationType(str, Enum):
    setup_change = "setup_change"
    part_design = "part_design"
    engine_map = "engine_map"
    tire_strategy = "tire_strategy"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Evidence(BaseModel):
    source: str
    type: EvidenceType
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str | None = None


class ToolCall(BaseModel):
    tool: str
    status: ToolStatus = ToolStatus.proposed
    approval_required: bool = False
    arguments: dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    type: RecommendationType
    summary: str
    risk: RiskLevel
    approval_required: bool
    evidence_refs: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    message: str
    role: str = "crew_chief"
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[ChatMessage] = Field(default_factory=list)


class RaceCommandCenterChatRequest(BaseModel):
    query: str
    user_role: str = "crew_chief"
    active_session_id: str | None = None
    circuit: str | None = None
    stint_id: str | None = None
    base_setup_id: str | None = None
    proposed_setup_id: str | None = None
    vehicle_context: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[ChatMessage] = Field(default_factory=list)


class CopilotResponse(BaseModel):
    message: str
    evidence: list[Evidence] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    approval_status: Literal["not_required", "required", "blocked"] = "not_required"
    next_step: str | None = None


class ToolCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    execute: bool = False
    approval_token: str | None = None


class SetupRecommendationRequest(BaseModel):
    circuit_type: str
    track_temperature_c: float | None = None
    symptoms: list[str] = Field(default_factory=list)
    current_setup: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class TelemetryAnalysisRequest(BaseModel):
    session_a: str
    session_b: str | None = None
    corner: str | None = None
    metrics: list[str] = Field(default_factory=list)
    lap_range: str | None = None


class PatternAnalysisRequest(BaseModel):
    query: str
    session_id: str | None = None
    lookback_sessions: int = 10


class CrewChiefReportRequest(BaseModel):
    session_id: str
    include_setup: bool = True
    include_anomalies: bool = True
    include_recommendations: bool = True
