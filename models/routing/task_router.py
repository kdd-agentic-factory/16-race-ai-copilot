"""Routes classified tasks to platform capabilities."""


ROUTES = {
    "setup_recommendation": ["rag-cag", "race-command-center", "orchestrator"],
    "telemetry_analysis": ["race-command-center", "rag-cag"],
    "crew_chief_report": ["race-command-center", "documentation-agent"],
    "general": ["rag-cag"],
}


def route(intent: str) -> list[str]:
    return ROUTES.get(intent, ROUTES["general"])
