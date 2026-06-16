from race_ai_copilot.models.ticketing import LifecycleState, SeverityLevel, TicketInput
from race_ai_copilot.services.ticket_copilot_service import TicketCopilotService


def test_ticket_copilot_returns_concise_summary_and_hints():
    service = TicketCopilotService()
    ticket = TicketInput(
        ticket_id="T-200",
        subject="Customer cannot log in after password reset",
        description="The portal rejects the new password on first sign-in.",
        queue="support",
        severity=SeverityLevel.high,
        age_hours=6,
        lifecycle_state=LifecycleState.waiting_customer,
        sla_remaining_minutes=30,
        customer_tier="enterprise",
        tags=["auth", "login", "reset"],
    )

    response = service.summarize(ticket)

    assert response.ticket_id == "T-200"
    assert response.summary
    assert len(response.summary) <= 180
    assert "login" in response.summary.lower() or "log in" in response.summary.lower()
    assert response.similar_case_hints
    assert response.recommended_next_actions
    assert any("password reset" in hint.lower() or "account access" in hint.lower() for hint in response.similar_case_hints)
    assert any("customer" in action.lower() or "assign" in action.lower() for action in response.recommended_next_actions)
