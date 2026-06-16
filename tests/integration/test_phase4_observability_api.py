from __future__ import annotations

from race_ai_copilot.main import app


def test_observability_endpoints_return_tenant_scoped_metrics():
    headers = {"X-Tenant-ID": "tenant-observability", "X-Request-ID": "req-observability-1"}
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        sla_response = client.post(
            "/api/v1/observability/sla-health",
            headers=headers,
            json={
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
                        "tenant_id": "tenant-observability",
                    }
                ]
            },
        )
        groundedness_response = client.post(
            "/api/v1/observability/groundedness",
            headers=headers,
            json={
                "answer": "Direct answer: evidence-backed.",
                "evidence": [{"source_id": "doc-1", "tenant_id": "tenant-observability"}],
            },
        )
        approval_response = client.post(
            "/api/v1/observability/approvals",
            headers=headers,
            json={"approvals": [{"required": True, "granted": False, "tenant_id": "tenant-observability"}]},
        )
        improvement_response = client.post(
            "/api/v1/observability/improvement-signals",
            headers=headers,
            json={
                "sla_health": sla_response.json(),
                "groundedness": groundedness_response.json(),
                "approvals": approval_response.json(),
            },
        )

        assert sla_response.status_code == 200
        assert sla_response.json()["metrics"]["breached"] == 1
        assert groundedness_response.json()["metrics"]["groundedness_score"] == 1.0
        assert approval_response.json()["metrics"]["blocked_rate"] == 1.0
        assert improvement_response.json()["tenant_id"] == "tenant-observability"
        assert improvement_response.json()["signals"]
