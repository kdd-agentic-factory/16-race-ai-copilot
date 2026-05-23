from typing import Any, Dict, List

# Keywords that trigger mandatory crew-chief approval.
CRITICAL_KEYWORDS: List[str] = [
    "mapping",
    "tire pressure",
    "suspension",
    "traction control",
    "apply",
    "approve",
    "cambiar setup",
]


class ApprovalGuard:
    """Intercepts critical race-engineering actions that require crew-chief approval.

    Scans both the raw user message and any structured recommendations for
    keywords that indicate a potentially dangerous or irreversible change.
    """

    def evaluate(self, message: str, recommendations: List[Any]) -> Dict[str, Any]:
        """Evaluate whether the message or its recommendations require approval.

        Args:
            message: The raw user message.
            recommendations: A list of recommendation objects (or strings).

        Returns:
            A dict with:
            - ``approval_required`` (bool): Whether crew chief approval is needed.
            - ``approver_role`` (str | None): The role responsible for approval.
        """
        message_lower = message.lower()
        for keyword in CRITICAL_KEYWORDS:
            if keyword in message_lower:
                return {"approval_required": True, "approver_role": "crew_chief"}

        # Also scan recommendations for critical language.
        for rec in recommendations:
            rec_text = str(rec).lower()
            for keyword in CRITICAL_KEYWORDS:
                if keyword in rec_text:
                    return {"approval_required": True, "approver_role": "crew_chief"}

        return {"approval_required": False, "approver_role": None}
