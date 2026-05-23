"""Approval compliance metric — checks that approval flags are correct."""

from __future__ import annotations

from typing import Any, Dict


class ApprovalComplianceMetric:
    """Evaluates whether the copilot correctly flagged (or didn't flag)
    a response as requiring crew-chief approval.

    This is a binary check: either the approval state matches the
    expected value or it doesn't.
    """

    def evaluate(
        self,
        response: Any,
        expected_approval: bool,
    ) -> bool:
        """Check that the response's approval status matches the
        expected value.

        Args:
            response: A ``ChatResponse`` (from schemas), a dict with an
                ``approval_required`` key, or any object that has an
                ``approval_required`` attribute.
            expected_approval: ``True`` if approval is expected,
                ``False`` otherwise.

        Returns:
            ``True`` if the response's ``approval_required`` field
            matches ``expected_approval``, ``False`` otherwise.
        """
        actual = self._get_approval_required(response)
        return actual == expected_approval

    def _get_approval_required(self, response: Any) -> bool:
        """Extract the ``approval_required`` flag from a response,
        handling various shapes."""
        if response is None:
            return False

        # Object with attribute (ChatResponse, etc.)
        if hasattr(response, "approval_required"):
            return bool(response.approval_required)

        # Dict
        if isinstance(response, dict):
            return bool(response.get("approval_required", False))

        return False

    def compliance_rate(
        self,
        results: list[dict],
    ) -> float:
        """Compute the compliance rate across multiple evaluations.

        Args:
            results: A list of dicts, each containing at least
                ``"response"`` and ``"expected_approval"`` keys.

        Returns:
            A float between 0.0 and 1.0 representing the fraction of
            evaluations that passed.
        """
        if not results:
            return 1.0

        passed = sum(
            1
            for r in results
            if self.evaluate(
                r.get("response"),
                r.get("expected_approval", False),
            )
        )
        return passed / len(results)
