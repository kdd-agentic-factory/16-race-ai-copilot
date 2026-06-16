from __future__ import annotations

from fastapi.testclient import TestClient

from race_ai_copilot.main import app


client = TestClient(app)


def test_command_center_integration_route_returns_proposed_tool_calls():
    payload = {
        "context": {
            "tenant": {
                "tenant_id": "tenant-42",
                "user_role": "crew_chief",
                "approval_scope": "read_only",
            },
            "request_id": "req-cc-1",
            "session_id": "ses-cc-1",
        },
        "reporting": {"report_type": "command_center_chat", "report_id": "rpt-cc-1"},
        "query": "Summarize the latest stint deltas for Jerez",
        "command_center_id": "cc-17",
        "vehicle_context": {"car_id": "car-01", "track": "Jerez"},
    }

    response = client.post("/api/v1/integrations/race-command-center/chat", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["evidence"][0]["source"] == "race-command-center:context"
    assert body["tool_calls"][0]["tool"] == "race_command_center.context.read"
    assert body["approval"]["required"] is False
    assert "operational" in body["next_step"].lower()


def test_sla_war_room_integration_route_returns_escalation_cohorts():
    payload = {
        "context": {
            "tenant": {
                "tenant_id": "tenant-99",
                "user_role": "crew_chief",
                "approval_scope": "propose",
            },
            "request_id": "req-war-1",
            "session_id": "ses-war-1",
        },
        "reporting": {"report_type": "sla_war_room", "report_id": "rpt-war-1"},
        "war_room_id": "wr-17",
        "topic": "SLA escalation review",
        "participants": ["oncall", "ops"],
        "payload": {
            "tickets": [
                {
                    "ticket_id": "T-breached",
                    "subject": "Payment outage",
                    "queue": "incident",
                    "severity": "critical",
                    "age_hours": 3,
                    "lifecycle_state": "in_progress",
                    "sla_remaining_minutes": -10,
                    "customer_tier": "enterprise",
                },
                {
                    "ticket_id": "T-risk",
                    "subject": "Login failures climbing",
                    "queue": "support",
                    "severity": "high",
                    "age_hours": 5,
                    "lifecycle_state": "new",
                    "sla_remaining_minutes": 25,
                    "customer_tier": "premium",
                },
            ]
        },
    }

    response = client.post("/api/v1/integrations/race-command-center/war-room", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "escalation_needed"
    assert body["metadata"]["cohorts"]["breached"] == ["T-breached"]
    assert body["metadata"]["cohorts"]["at_risk"] == ["T-risk"]
    assert body["approval"]["required"] is True
