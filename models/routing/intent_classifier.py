"""Lightweight intent classifier placeholder for the copilot MVP."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float


def classify(text: str) -> IntentResult:
    lowered = text.lower()
    if "setup" in lowered or "rebote" in lowered:
        return IntentResult("setup_recommendation", 0.75)
    if "telemet" in lowered or "fp1" in lowered or "fp2" in lowered:
        return IntentResult("telemetry_analysis", 0.75)
    if "informe" in lowered:
        return IntentResult("crew_chief_report", 0.7)
    return IntentResult("general", 0.5)
