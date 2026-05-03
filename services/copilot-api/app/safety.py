HIGH_RISK_TERMS = [
    "setup",
    "rebote",
    "suspensión",
    "brake bias",
    "mapa motor",
    "despliegue",
    "kubernetes",
    "github",
    "producción",
]


def requires_human_approval(text: str) -> bool:
    normalized = text.lower()
    return any(term in normalized for term in HIGH_RISK_TERMS)


def approval_status(text: str) -> str:
    return "required" if requires_human_approval(text) else "not_required"
