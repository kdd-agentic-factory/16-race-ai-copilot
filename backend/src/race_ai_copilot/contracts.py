"""Canonical boundary contracts for the Race AI Copilot backend.

These models normalize the envelope shape shared by the Copilot, Queue,
War Room, approval, tenant, and reporting surfaces so downstream services
can receive a consistent context object regardless of entry point.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ApprovalScope(str, Enum):
    read_only = "read_only"
    propose = "propose"
    approve = "approve"
    execute = "execute"


class TenantMetadata(BaseModel):
    tenant_id: str
    user_role: str = "viewer"
    approval_scope: ApprovalScope = ApprovalScope.propose


class ReportingMetadata(BaseModel):
    report_type: str
    report_id: str | None = None
    source_system: str = "race_ai_copilot"
    correlation_id: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: dict[str, str] = Field(default_factory=dict)


class ApprovalMetadata(BaseModel):
    required: bool = False
    granted: bool = False
    scope: ApprovalScope = ApprovalScope.propose
    approver_role: str | None = None
    reason: str | None = None


class KnowledgeCitation(BaseModel):
    source_id: str
    title: str
    snippet: str
    url_or_path: str | None = None
    confidence: float = 0.0
    tenant_id: str = "tenant-default"
    request_id: str | None = None
    session_id: str | None = None
    correlation_id: str | None = None
    fallback_used: bool = False

    @property
    def summary(self) -> str:
        return self.snippet


class KnowledgeRetrievalResult(BaseModel):
    query: str
    citations: list[KnowledgeCitation] = Field(default_factory=list)
    fallback_used: bool = False
    audit: dict[str, Any] = Field(default_factory=dict)


class ToolAuditMetadata(BaseModel):
    tenant_id: str
    user_role: str = "viewer"
    request_scope: ApprovalScope = ApprovalScope.propose
    request_id: str | None = None
    session_id: str | None = None
    correlation_id: str | None = None
    source: str = "race_ai_copilot"
    approved: bool = False
    critical: bool = False


class TypedMCPToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: RequestContext
    audit: ToolAuditMetadata
    approval_required: bool = False
    status: Literal["proposed", "blocked", "executed"] = "proposed"

    @classmethod
    def from_context(
        cls,
        *,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        context: RequestContext,
        audit_source: str = "race_ai_copilot",
        approval_required: bool = False,
        status: Literal["proposed", "blocked", "executed"] = "proposed",
    ) -> "TypedMCPToolCall":
        return cls(
            tool_name=tool_name,
            arguments=arguments or {},
            context=context,
            audit=ToolAuditMetadata(
                tenant_id=context.tenant_id,
                user_role=context.user_role,
                request_scope=context.approval_scope,
                request_id=context.request_id,
                session_id=context.session_id,
                correlation_id=context.correlation_id,
                source=audit_source,
                approved=False,
                critical=approval_required,
            ),
            approval_required=approval_required,
            status=status,
        )


class AgentDispatchPlan(BaseModel):
    workflow: str
    agent_name: str
    tool_calls: list[TypedMCPToolCall] = Field(default_factory=list)
    citations: list[KnowledgeCitation] = Field(default_factory=list)


class RequestContext(BaseModel):
    tenant: TenantMetadata
    request_id: str | None = None
    session_id: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def tenant_id(self) -> str:
        return self.tenant.tenant_id

    @property
    def user_role(self) -> str:
        return self.tenant.user_role

    @property
    def approval_scope(self) -> ApprovalScope:
        return self.tenant.approval_scope

    @classmethod
    def from_values(
        cls,
        *,
        tenant_id: str,
        user_role: str = "viewer",
        approval_scope: ApprovalScope | str = ApprovalScope.propose,
        request_id: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "RequestContext":
        return cls(
            tenant=TenantMetadata(
                tenant_id=tenant_id,
                user_role=user_role,
                approval_scope=ApprovalScope(approval_scope),
            ),
            request_id=request_id,
            session_id=session_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )


class _EnvelopeBase(BaseModel):
    context: RequestContext
    reporting: ReportingMetadata | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandCenterRequestEnvelope(_EnvelopeBase):
    kind: Literal["command_center"] = "command_center"
    query: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)
    command_center_id: str | None = None
    vehicle_context: dict[str, Any] = Field(default_factory=dict)


class CommandCenterResponseEnvelope(_EnvelopeBase):
    kind: Literal["command_center"] = "command_center"
    answer: str = ""
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    approval: ApprovalMetadata = Field(default_factory=ApprovalMetadata)
    next_step: str | None = None


class QueueRequestEnvelope(_EnvelopeBase):
    kind: Literal["queue"] = "queue"
    queue_name: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
    max_items: int | None = None


class QueueResponseEnvelope(_EnvelopeBase):
    kind: Literal["queue"] = "queue"
    ranked_items: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    total_items: int = 0
    active_items: int = 0


class WarRoomRequestEnvelope(_EnvelopeBase):
    kind: Literal["war_room"] = "war_room"
    war_room_id: str = ""
    topic: str = ""
    participants: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class WarRoomResponseEnvelope(_EnvelopeBase):
    kind: Literal["war_room"] = "war_room"
    status: str = ""
    next_actions: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    approval: ApprovalMetadata = Field(default_factory=ApprovalMetadata)


class ApprovalRequestEnvelope(_EnvelopeBase):
    kind: Literal["approval"] = "approval"
    subject: str = ""
    reason: str = ""
    approval: ApprovalMetadata = Field(default_factory=ApprovalMetadata)


class ApprovalResponseEnvelope(_EnvelopeBase):
    kind: Literal["approval"] = "approval"
    approval_status: Literal["not_required", "required", "granted", "blocked"] = "not_required"
    approver_role: str | None = None
    decision_notes: list[str] = Field(default_factory=list)
