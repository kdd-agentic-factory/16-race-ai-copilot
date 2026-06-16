from __future__ import annotations

import os

os.environ.setdefault("INSFORGE_AUTH_ENABLED", "false")

from fastapi.testclient import TestClient

from race_ai_copilot.config import get_settings
from race_ai_copilot.main import app as canonical_app
from race_ai_copilot.models.legacy import (
    ChatMessage,
    ChatRequest,
    CrewChiefReportRequest,
    EvidenceType,
    PatternAnalysisRequest,
    RecommendationType,
    RiskLevel,
    SetupRecommendationRequest,
    TelemetryAnalysisRequest,
    ToolCallRequest,
    ToolStatus,
)
from race_ai_copilot.services.legacy_surface_service import LegacySurfaceService


def test_health_reports_default_model_from_env_aliases(monkeypatch):
    for env_name in ("DEFAULT_MODEL", "COPILOT_DEFAULT_MODEL"):
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)
        monkeypatch.delenv("COPILOT_DEFAULT_MODEL", raising=False)
        monkeypatch.setenv(env_name, "legacy-model")
        get_settings.cache_clear()

        with TestClient(canonical_app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["default_model"] == "legacy-model"
        assert payload["version"] == "0.1.0"
        assert payload["timestamp"]

    get_settings.cache_clear()


def test_canonical_app_exposes_legacy_root_routes():
    paths = {route.path for route in canonical_app.routes}

    assert "/chat" in paths
    assert "/chat/stream" in paths
    assert "/integrations/race-command-center/chat" in paths
    assert "/tools/call" in paths
    assert "/recommendations/setup" in paths
    assert "/analysis/telemetry" in paths
    assert "/analysis/patterns" in paths
    assert "/reports/crew-chief" in paths


def test_legacy_surface_chat_and_stream_behave_like_prototype():
    service = LegacySurfaceService()

    response = service.build_chat_response(
        ChatRequest(
            message="Necesito setup por rebote",
            role="crew_chief",
            history=[ChatMessage(role="user", content="hola")],
        )
    )

    assert response.approval_status == "required"
    assert response.recommendations[0].type == RecommendationType.setup_change
    assert response.tool_calls[0].status == ToolStatus.proposed

    stream_events = list(service.stream_chat_response(response))
    assert stream_events[-1] == "event: done\ndata: [DONE]\n\n"
    assert any(event.startswith("data: Direct answer:") for event in stream_events)


def test_legacy_surface_tooling_and_reports_match_legacy_behavior():
    service = LegacySurfaceService()

    blocked = service.call_tool(ToolCallRequest(tool="session.create", execute=True))
    approved = service.call_tool(
        ToolCallRequest(tool="session.create", execute=True, approval_token="token-123")
    )

    assert blocked.approval_status == "blocked"
    assert blocked.tool_calls[0].status == ToolStatus.blocked
    assert approved.approval_status == "not_required"
    assert approved.tool_calls[0].status == ToolStatus.proposed

    setup_high = service.build_setup_recommendation(
        SetupRecommendationRequest(circuit_type="street", track_temperature_c=42, symptoms=["understeer"])
    )
    setup_medium = service.build_setup_recommendation(
        SetupRecommendationRequest(circuit_type="street", track_temperature_c=35, symptoms=[])
    )

    assert setup_high.recommendations[0].risk == RiskLevel.high
    assert setup_medium.recommendations[0].risk == RiskLevel.medium

    from app import copilot as legacy_copilot

    shim_response = legacy_copilot.build_setup_recommendation(
        "street",
        42,
        ["understeer"],
    )

    assert shim_response.model_dump() == setup_high.model_dump()

    telemetry = service.build_telemetry_analysis(
        TelemetryAnalysisRequest(session_a="FP1", session_b="FP2", corner="T1")
    )
    patterns = service.build_pattern_analysis(PatternAnalysisRequest(query="brake fade", lookback_sessions=3))
    crew_report = service.build_crew_chief_report(CrewChiefReportRequest(session_id="sess-42"))

    assert telemetry.evidence[0].type == EvidenceType.telemetry
    assert telemetry.tool_calls[0].tool == "telemetry.compare"
    assert patterns.tool_calls[0].tool == "patterns.search"
    assert "3 sessions" in patterns.message
    assert crew_report.evidence[0].source == "session:sess-42"


def test_legacy_surface_telemetry_analysis_includes_comparison_context():
    service = LegacySurfaceService()

    telemetry = service.build_telemetry_analysis(
        TelemetryAnalysisRequest(session_a="FP1", session_b="FP2", corner="T1")
    )

    assert telemetry.message == "Telemetry analysis proposed for FP1 vs FP2 at T1. No telemetry evidence is invented by the API stub."
    assert telemetry.tool_calls[0].tool == "telemetry.compare"


def test_legacy_entrypoint_reexports_canonical_api_paths():
    from app.main import app as legacy_app

    paths = {route.path for route in legacy_app.routes}

    assert "/api/v1/chat" in paths
    assert "/api/v1/integrations/race-command-center/chat" in paths
    assert "/api/v1/observability/sla-health" in paths
