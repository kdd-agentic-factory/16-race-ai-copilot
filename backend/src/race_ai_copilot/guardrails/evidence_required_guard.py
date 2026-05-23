from typing import Any, Dict


class EvidenceRequiredGuard:
    """Validates that a response is grounded in collected evidence.

    When ``require_evidence`` is ``True``, the guard checks that the
    evidence object is non-empty before allowing the response through.
    """

    def evaluate(
        self,
        answer: str,
        evidence: Any,
        require_evidence: bool = True,
    ) -> Dict[str, Any]:
        """Check whether evidence is present when required.

        Args:
            answer: The generated response text.
            evidence: The evidence object (can be a list, a model, or ``None``).
            require_evidence: Whether evidence is mandatory for this response.

        Returns:
            A dict with:
            - ``passed`` (bool): ``False`` when evidence is required but missing.
        """
        if not require_evidence:
            return {"passed": True}

        # --- Check various evidence shapes ---
        if evidence is None:
            return {"passed": False}

        if isinstance(evidence, list):
            return {"passed": len(evidence) > 0}

        if hasattr(evidence, "sources") and hasattr(evidence, "raw_data"):
            # Duck-type EvidencePacket
            return {"passed": bool(evidence.sources or evidence.raw_data)}

        # For plain dicts, check they have content
        if isinstance(evidence, dict):
            return {"passed": bool(evidence.get("sources") or evidence.get("raw_data"))}

        # Treat any truthy value as passed
        return {"passed": bool(evidence)}
