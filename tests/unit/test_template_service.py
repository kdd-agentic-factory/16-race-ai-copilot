from __future__ import annotations

from race_ai_copilot.services.template_service import FileTemplateService


def test_template_service_renders_versioned_templates():
    service = FileTemplateService()

    template = service.get("crew_chief_report")
    assert template.version == "v1"

    rendered = service.render(
        "crew_chief_report",
        variables={
            "session_id": "ses-77",
            "summary": "Stable lap times and one setup question.",
            "anomalies": "None",
            "setup_notes": "Front wing kept at baseline.",
            "recommendations": "Continue monitoring tyre wear.",
            "evidence": "[1] telemetry snapshot",
        },
    )

    assert "Session: ses-77" in rendered
    assert "Stable lap times" in rendered
    assert "template-version: v1" in rendered
