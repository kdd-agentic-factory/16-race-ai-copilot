from __future__ import annotations

from fastapi.testclient import TestClient

from race_ai_copilot.main import app


def test_legacy_setup_recommendation_route_returns_successful_response():
    payload = {
        "circuit_type": "street",
        "track_temperature_c": 42,
        "symptoms": ["understeer", "front_tyre_overheat"],
        "current_setup": {"front_ride_height_mm": 55, "rear_ride_height_mm": 60},
    }

    with TestClient(app) as client:
        response = client.post("/recommendations/setup", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["approval_status"] == "required"
    assert body["recommendations"][0]["type"] == "setup_change"
    assert body["recommendations"][0]["approval_required"] is True
    assert body["evidence"][0]["source"] == "telemetry:required"
    assert body["next_step"]
