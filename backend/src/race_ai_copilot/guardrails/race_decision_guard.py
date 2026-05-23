import re
from typing import Dict, List, Tuple

# Phrases the AI must never utter without human approval.
# Each entry maps a regex pattern to its safe replacement.
# We use case-insensitive matching so that "The change is approved"
# and "the change is approved" are both caught.
FORBIDDEN_PHRASES: List[Tuple[str, str]] = [
    (r"\bthe change is approved\b", "this requires crew chief approval"),
    (r"\bapply the setup\b", "this requires crew chief approval"),
    (r"\bthe decision is final\b", "this requires crew chief approval"),
]


class RaceDecisionGuard:
    """Sanitizes AI responses to prevent unauthorized race decisions.

    Scans the answer for phrases that imply a decision has been made
    autonomously and replaces them with a safe deferral message.
    Matching is case-insensitive to handle natural language variation.
    """

    def sanitize(self, answer: str) -> str:
        """Replace forbidden decision phrases with safe alternatives.

        Args:
            answer: The raw generated response.

        Returns:
            The sanitized response with all forbidden phrases replaced.
        """
        sanitized = answer
        for pattern, replacement in FORBIDDEN_PHRASES:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
