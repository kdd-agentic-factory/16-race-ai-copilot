from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    tools: list[str]
    approval_required: bool = False


def classify_intent(message: str) -> Intent:
    text = message.lower()
    if any(token in text for token in ["setup", "rebote", "click", "neumático", "degrad"]):
        return Intent("setup_recommendation", ["rag.query", "telemetry.analyze", "orchestrator.approval"], True)
    if any(token in text for token in ["fp1", "fp2", "telemet", "curva", "mapa motor"]):
        return Intent("telemetry_analysis", ["telemetry.compare", "rag.query"])
    if any(token in text for token in ["adr", "arquitectura", "kafka", "redpanda"]):
        return Intent("documentation", ["rag.query", "documentation.generate"])
    if any(token in text for token in ["patrones", "similar", "sesiones anteriores"]):
        return Intent("pattern_discovery", ["patterns.search", "rag.query"])
    if any(token in text for token in ["informe", "crew chief", "anomal"]):
        return Intent("crew_chief_report", ["telemetry.analyze", "reports.generate"])
    return Intent("general_race_copilot", ["rag.query"])
