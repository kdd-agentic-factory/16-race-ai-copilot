from race_ai_copilot.models.ticketing import LifecycleState, SeverityLevel, TicketInput
from race_ai_copilot.services.smart_queue_service import SmartQueueService, SmartQueueRequest


def test_smart_queue_ranks_breached_and_critical_first():
    service = SmartQueueService()
    request = SmartQueueRequest(
        tickets=[
            TicketInput(
                ticket_id="T-100",
                subject="Login issue after password reset",
                queue="support",
                severity=SeverityLevel.high,
                age_hours=12,
                lifecycle_state=LifecycleState.in_progress,
                sla_remaining_minutes=45,
                customer_tier="premium",
                tags=["auth", "login"],
            ),
            TicketInput(
                ticket_id="T-101",
                subject="Production outage in billing",
                queue="incident",
                severity=SeverityLevel.critical,
                age_hours=2,
                lifecycle_state=LifecycleState.in_progress,
                sla_remaining_minutes=-5,
                customer_tier="enterprise",
                tags=["billing", "outage"],
            ),
            TicketInput(
                ticket_id="T-102",
                subject="Minor typo in docs",
                queue="backlog",
                severity=SeverityLevel.low,
                age_hours=36,
                lifecycle_state=LifecycleState.new,
                sla_remaining_minutes=240,
                customer_tier="standard",
                tags=["docs"],
            ),
        ]
    )

    response = service.rank(request)

    assert [item.ticket.ticket_id for item in response.ranked_tickets] == ["T-101", "T-100", "T-102"]
    assert response.ranked_tickets[0].sla_status.value == "breached"
    assert any("SLA breached" in reason for reason in response.ranked_tickets[0].reasons)
    assert response.summary.startswith("Ranked 3 active tickets")
