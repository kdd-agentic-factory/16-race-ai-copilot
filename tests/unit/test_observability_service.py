from __future__ import annotations

from race_ai_copilot.contracts import ApprovalScope, RequestContext
from race_ai_copilot.models.ticketing import LifecycleState, SeverityLevel, TicketInput
from race_ai_copilot.services.observability_service import ObservabilityService


def test_observability_service_builds_tenant_scoped_payloads():
    service = ObservabilityService()
    context = RequestContext.from_values(
        tenant_id="tenant-observability",
        user_role="crew_chief",
        approval_scope=ApprovalScope.propose,
    )

    sla_report = service.sla_health(
        tickets=[
            TicketInput(
                ticket_id="T-breached",
                subject="Payment outage",
                queue="incident",
                severity=SeverityLevel.critical,
                age_hours=3,
                lifecycle_state=LifecycleState.in_progress,
                sla_remaining_minutes=-10,
                customer_tier="enterprise",
                tenant_id="tenant-observability",
            ),
            TicketInput(
                ticket_id="T-foreign",
                subject="Ignore me",
                queue="support",
                severity=SeverityLevel.low,
                tenant_id="tenant-other",
            ),
        ],
        context=context,
    )

    groundedness_report = service.groundedness(
        answer="Direct answer: evidence-backed.",
        evidence=[{"source_id": "doc-1", "tenant_id": "tenant-observability"}],
        context=context,
    )

    approval_report = service.approvals(
        approvals=[
            {"required": True, "granted": False, "tenant_id": "tenant-observability"},
            {"required": True, "granted": True, "tenant_id": "tenant-other"},
        ],
        context=context,
    )

    improvement_report = service.improvement_signals(
        sla_health=sla_report,
        groundedness=groundedness_report,
        approvals=approval_report,
        context=context,
    )

    assert sla_report["tenant_id"] == "tenant-observability"
    assert sla_report["metrics"]["breached"] == 1
    assert groundedness_report["metrics"]["groundedness_score"] == 1.0
    assert approval_report["metrics"]["blocked_rate"] == 1.0
    assert improvement_report["signals"]
