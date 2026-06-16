from __future__ import annotations

from race_ai_copilot.contracts import (
    ApprovalScope,
    CommandCenterRequestEnvelope,
    ReportingMetadata,
    RequestContext,
    WarRoomRequestEnvelope,
)
from race_ai_copilot.models.ticketing import (
    LifecycleState,
    SeverityLevel,
    SmartQueueRequest,
    TicketInput,
)
from race_ai_copilot.services.command_center_service import CommandCenterService
from race_ai_copilot.services.smart_queue_service import SmartQueueService
from race_ai_copilot.services.ticket_copilot_service import TicketCopilotService
from race_ai_copilot.services.sla_war_room_service import SlaWarRoomService


def test_command_center_service_routes_read_only_context_without_operational_writes():
    service = CommandCenterService()
    context = RequestContext.from_values(
        tenant_id="tenant-42",
        user_role="crew_chief",
        approval_scope=ApprovalScope.read_only,
        session_id="ses-42",
        request_id="req-42",
        correlation_id="corr-42",
    )
    request = CommandCenterRequestEnvelope(
        context=context,
        reporting=ReportingMetadata(report_type="command_center_chat", report_id="rpt-42"),
        query="Summarize the latest stint deltas for Jerez",
        command_center_id="cc-17",
        vehicle_context={"car_id": "car-01", "track": "Jerez"},
        history=[{"role": "user", "content": "How risky is the proposed setup?"}],
    )

    response = service.route(request)

    assert response.context.tenant_id == "tenant-42"
    assert response.answer.startswith("Direct answer:")
    assert response.evidence[0]["source"] == "race-command-center:context"
    assert response.tool_calls[0]["tool"] == "race_command_center.context.read"
    assert all(call["status"] == "proposed" for call in response.tool_calls)
    assert response.approval.required is False
    assert "operational" in response.next_step.lower()


def test_command_center_service_marks_setup_changes_as_approval_required():
    service = CommandCenterService()
    context = RequestContext.from_values(
        tenant_id="tenant-42",
        user_role="crew_chief",
        approval_scope=ApprovalScope.propose,
        session_id="ses-43",
        request_id="req-43",
    )
    request = CommandCenterRequestEnvelope(
        context=context,
        reporting=ReportingMetadata(report_type="command_center_chat", report_id="rpt-43"),
        query="Increase front wing by 2 degrees for qualifying pace",
        command_center_id="cc-17",
        vehicle_context={"car_id": "car-01", "track": "Jerez"},
    )

    response = service.route(request)

    assert response.approval.required is True
    assert response.approval.reason
    assert any("setup" in recommendation["summary"].lower() or "wing" in recommendation["summary"].lower() for recommendation in response.recommendations)


def test_smart_queue_orders_by_sla_then_severity_within_band():
    service = SmartQueueService()
    request = SmartQueueRequest(
        tickets=[
            TicketInput(
                ticket_id="T-healthy-critical",
                subject="Healthy but urgent incident",
                queue="incident",
                severity=SeverityLevel.critical,
                age_hours=1,
                lifecycle_state=LifecycleState.in_progress,
                sla_remaining_minutes=180,
                customer_tier="enterprise",
            ),
            TicketInput(
                ticket_id="T-at-risk-low",
                subject="Minor issue nearing SLA",
                queue="support",
                severity=SeverityLevel.low,
                age_hours=4,
                lifecycle_state=LifecycleState.new,
                sla_remaining_minutes=20,
                customer_tier="standard",
            ),
            TicketInput(
                ticket_id="T-breached-medium",
                subject="Breach already happened",
                queue="incident",
                severity=SeverityLevel.medium,
                age_hours=2,
                lifecycle_state=LifecycleState.in_progress,
                sla_remaining_minutes=-5,
                customer_tier="premium",
            ),
        ]
    )

    response = service.rank(request)

    assert [item.ticket.ticket_id for item in response.ranked_tickets] == [
        "T-breached-medium",
        "T-at-risk-low",
        "T-healthy-critical",
    ]
    assert response.ranked_tickets[0].recommended_action.startswith("Escalate")
    assert response.ranked_tickets[0].sla_status.value == "breached"
    assert response.summary.startswith("Ranked 3 active tickets")


def test_ticket_copilot_includes_escalation_hints_when_sla_is_breached():
    service = TicketCopilotService()
    ticket = TicketInput(
        ticket_id="T-200",
        subject="Customer cannot log in after password reset",
        description="The portal rejects the new password on first sign-in.",
        queue="support",
        severity=SeverityLevel.high,
        age_hours=6,
        lifecycle_state=LifecycleState.waiting_customer,
        sla_remaining_minutes=-15,
        customer_tier="enterprise",
        tags=["auth", "login", "reset"],
    )

    response = service.summarize(ticket)

    assert response.ticket_id == "T-200"
    assert response.summary
    assert len(response.summary) <= 180
    assert response.escalation_hints
    assert any("on-call" in hint.lower() or "escalat" in hint.lower() for hint in response.escalation_hints)
    assert any("customer" in action.lower() or "assign" in action.lower() for action in response.recommended_next_actions)


def test_sla_war_room_groups_breached_and_at_risk_tickets_into_escalation_cohorts():
    service = SlaWarRoomService()
    context = RequestContext.from_values(
        tenant_id="tenant-99",
        user_role="crew_chief",
        approval_scope=ApprovalScope.propose,
        session_id="ses-war-room",
        request_id="req-war-room",
    )
    request = WarRoomRequestEnvelope(
        context=context,
        reporting=ReportingMetadata(report_type="sla_war_room", report_id="rpt-war-room"),
        war_room_id="wr-17",
        topic="SLA escalation review",
        participants=["oncall", "ops"],
        payload={
            "tickets": [
                TicketInput(
                    ticket_id="T-breached",
                    subject="Payment outage",
                    queue="incident",
                    severity=SeverityLevel.critical,
                    age_hours=3,
                    lifecycle_state=LifecycleState.in_progress,
                    sla_remaining_minutes=-10,
                    customer_tier="enterprise",
                ).model_dump(),
                TicketInput(
                    ticket_id="T-risk",
                    subject="Login failures climbing",
                    queue="support",
                    severity=SeverityLevel.high,
                    age_hours=5,
                    lifecycle_state=LifecycleState.new,
                    sla_remaining_minutes=25,
                    customer_tier="premium",
                ).model_dump(),
                TicketInput(
                    ticket_id="T-healthy",
                    subject="Minor documentation update",
                    queue="backlog",
                    severity=SeverityLevel.low,
                    age_hours=12,
                    lifecycle_state=LifecycleState.new,
                    sla_remaining_minutes=240,
                    customer_tier="standard",
                ).model_dump(),
            ]
        },
    )

    response = service.route(request)

    assert response.status == "escalation_needed"
    assert response.metadata["cohorts"]["breached"] == ["T-breached"]
    assert response.metadata["cohorts"]["at_risk"] == ["T-risk"]
    assert response.next_actions[0].startswith("Escalate")
    assert response.approval.required is True
