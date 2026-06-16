from fastapi.testclient import TestClient

from race_ai_copilot.main import app


client = TestClient(app)


def test_smart_queue_endpoint_returns_ranked_tickets():
    payload = {
        "tickets": [
            {
                "ticket_id": "T-301",
                "subject": "Billing outage for enterprise customer",
                "queue": "incident",
                "severity": "critical",
                "age_hours": 2,
                "lifecycle_state": "in_progress",
                "sla_remaining_minutes": -10,
                "customer_tier": "enterprise",
                "tags": ["billing", "outage"],
            },
            {
                "ticket_id": "T-302",
                "subject": "Need access after password reset",
                "queue": "support",
                "severity": "high",
                "age_hours": 8,
                "lifecycle_state": "waiting_customer",
                "sla_remaining_minutes": 25,
                "customer_tier": "premium",
                "tags": ["auth", "login"],
            },
        ]
    }

    response = client.post("/api/v1/smart-queue", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["ranked_tickets"][0]["ticket"]["ticket_id"] == "T-301"
    assert body["ranked_tickets"][0]["sla_status"] == "breached"
    assert body["summary"].startswith("Ranked 2 active tickets")


def test_ticket_copilot_endpoint_returns_summary_fields():
    payload = {
        "ticket": {
            "ticket_id": "T-303",
            "subject": "Portal login failure after password reset",
            "description": "User cannot authenticate with the new password.",
            "queue": "support",
            "severity": "high",
            "age_hours": 4,
            "lifecycle_state": "waiting_customer",
            "sla_remaining_minutes": 20,
            "customer_tier": "enterprise",
            "tags": ["auth", "login", "reset"],
        }
    }

    response = client.post("/api/v1/ticket-copilot", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "T-303"
    assert body["summary"]
    assert body["similar_case_hints"]
    assert body["recommended_next_actions"]
