from __future__ import annotations

from dataclasses import dataclass

import pytest

from race_ai_copilot.contracts import (
    ApprovalRequestEnvelope,
    ApprovalResponseEnvelope,
    ApprovalScope,
    CommandCenterRequestEnvelope,
    CommandCenterResponseEnvelope,
    QueueRequestEnvelope,
    QueueResponseEnvelope,
    ReportingMetadata,
    RequestContext,
    TenantMetadata,
    WarRoomRequestEnvelope,
    WarRoomResponseEnvelope,
)
from race_ai_copilot.auth_deps import Principal, build_request_context
from race_ai_copilot.interfaces import (
    KnowledgeService,
    ReportingService,
    TemplateService,
    ToolService,
)


@pytest.mark.parametrize(
    "factory, payload_key, payload_value",
    [
        (
            CommandCenterRequestEnvelope,
            "query",
            "Explain the latest stint deltas",
        ),
        (
            QueueRequestEnvelope,
            "queue_name",
            "incident",
        ),
        (
            WarRoomRequestEnvelope,
            "war_room_id",
            "wr-17",
        ),
        (
            ApprovalRequestEnvelope,
            "subject",
            "Apply setup change",
        ),
    ],
)
def test_canonical_request_envelopes_normalize_shared_context(factory, payload_key, payload_value):
    context = RequestContext.from_values(
        tenant_id="tenant-42",
        user_role="crew_chief",
        approval_scope=ApprovalScope.approve,
        session_id="ses-99",
        request_id="req-100",
    )
    reporting = ReportingMetadata(report_type="crew_chief_report", report_id="rpt-100")

    envelope = factory(
        context=context,
        reporting=reporting,
        **{
            payload_key: payload_value,
        },
    )

    assert envelope.context.tenant_id == "tenant-42"
    assert envelope.context.user_role == "crew_chief"
    assert envelope.context.approval_scope is ApprovalScope.approve
    assert envelope.reporting.report_id == "rpt-100"
    assert getattr(envelope, payload_key) == payload_value


@pytest.mark.parametrize(
    "factory, payload_key, payload_value, response_factory, response_key, response_value",
    [
        (
            CommandCenterRequestEnvelope,
            "query",
            "Summarize the session",
            CommandCenterResponseEnvelope,
            "answer",
            "Grounded summary",
        ),
        (
            QueueRequestEnvelope,
            "queue_name",
            "support",
            QueueResponseEnvelope,
            "summary",
            "Ranked queue",
        ),
        (
            WarRoomRequestEnvelope,
            "war_room_id",
            "war-1",
            WarRoomResponseEnvelope,
            "status",
            "active",
        ),
        (
            ApprovalRequestEnvelope,
            "subject",
            "Launch simulation",
            ApprovalResponseEnvelope,
            "approval_status",
            "required",
        ),
    ],
)
def test_canonical_response_envelopes_retain_tenant_and_reporting_metadata(
    factory,
    payload_key,
    payload_value,
    response_factory,
    response_key,
    response_value,
):
    context = RequestContext.from_values(
        tenant_id="tenant-7",
        user_role="analyst",
        approval_scope=ApprovalScope.propose,
    )
    reporting = ReportingMetadata(report_type="race_command_center_report", report_id="rpt-200")

    request_envelope = factory(
        context=context,
        reporting=reporting,
        **{payload_key: payload_value},
    )

    response_envelope = response_factory(
        context=request_envelope.context,
        reporting=request_envelope.reporting,
        **{response_key: response_value},
    )

    assert response_envelope.context.tenant_id == "tenant-7"
    assert response_envelope.context.user_role == "analyst"
    assert response_envelope.reporting.report_type == "race_command_center_report"
    assert getattr(response_envelope, response_key) == response_value


def test_request_context_from_values_preserves_tenant_role_and_scope():
    context = RequestContext.from_values(
        tenant_id="tenant-99",
        user_role="viewer",
        approval_scope="read_only",
        metadata={"source": "headers"},
    )

    assert context.tenant == TenantMetadata(
        tenant_id="tenant-99",
        user_role="viewer",
        approval_scope=ApprovalScope.read_only,
    )
    assert context.tenant_id == "tenant-99"
    assert context.user_role == "viewer"
    assert context.approval_scope is ApprovalScope.read_only
    assert context.metadata == {"source": "headers"}


def test_request_context_plumbing_combines_principal_and_headers():
    principal = Principal(user_id="u-77", role="race_engineer")

    context = build_request_context(
        tenant_id="tenant-55",
        principal=principal,
        session_id="ses-55",
        request_id="req-55",
        approval_scope="execute",
        metadata={"transport": "http"},
    )

    assert context.tenant_id == "tenant-55"
    assert context.user_role == "race_engineer"
    assert context.approval_scope is ApprovalScope.execute
    assert context.session_id == "ses-55"
    assert context.request_id == "req-55"
    assert context.metadata == {"transport": "http"}


@dataclass
class _KnowledgeImpl:
    async def search(self, query: str, context: RequestContext | None = None, limit: int = 5):
        return []


@dataclass
class _TemplateImpl:
    def render(self, template_name: str, context: RequestContext | None = None, variables=None):
        return template_name


@dataclass
class _ToolImpl:
    async def plan(self, tool_name: str, context: RequestContext | None = None, arguments=None):
        return []


@dataclass
class _ReportingImpl:
    def generate(self, report_type: str, context: RequestContext | None = None, metadata=None):
        return {}


def test_shared_service_interfaces_are_structural_and_context_aware():
    assert isinstance(_KnowledgeImpl(), KnowledgeService)
    assert isinstance(_TemplateImpl(), TemplateService)
    assert isinstance(_ToolImpl(), ToolService)
    assert isinstance(_ReportingImpl(), ReportingService)
