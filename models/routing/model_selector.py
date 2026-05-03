"""Selects Ollama model profiles for copilot roles."""


ROLE_TO_PROFILE = {
    "crew_chief": "crew_chief",
    "data_engineer": "data_engineer",
    "paper_writer": "paper_writer",
}


def select_profile(role: str) -> str:
    return ROLE_TO_PROFILE.get(role, "fast_assistant")
