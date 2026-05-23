"""Tool precision metric — measures precision and recall of tool calls."""

from __future__ import annotations

from typing import Dict, List


class ToolPrecisionMetric:
    """Evaluates the accuracy of tool calls made during a copilot
    response.

    Compares the set of tools that were actually called against the
    set of tools that were expected for the given user intent.

    Reports both **precision** (how many called tools were relevant)
    and **recall** (how many relevant tools were called). The
    ``evaluate`` method returns a combined F1-score by default.
    """

    def evaluate(
        self,
        called_tools: List[str],
        expected_tools: List[str],
    ) -> float:
        """Compute the F1 score for tool call accuracy.

        Precision = |called ∩ expected| / |called| (or 1.0 if no tools
                     were called and none were expected).
        Recall    = |called ∩ expected| / |expected| (or 1.0 if no
                     tools were expected).

        The F1 score is the harmonic mean of precision and recall.

        Args:
            called_tools: The list of tool names that were actually
                called (e.g. from ``ChatResponse.tool_calls``).
            expected_tools: The list of tool names that were expected
                for the user's intent.

        Returns:
            A float between 0.0 (no overlap) and 1.0 (perfect match).
        """
        called_set: set = set(called_tools or [])
        expected_set: set = set(expected_tools or [])

        intersection = called_set & expected_set

        # Precision: avoid division by zero
        if not called_set and not expected_set:
            return 1.0
        precision = (
            len(intersection) / len(called_set) if called_set else 0.0
        )

        # Recall
        recall = (
            len(intersection) / len(expected_set) if expected_set else 1.0
        )

        # F1 score
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def precision(self, called_tools: List[str], expected_tools: List[str]) -> float:
        """Compute only the precision score."""
        called_set: set = set(called_tools or [])
        expected_set: set = set(expected_tools or [])

        if not called_set:
            return 1.0 if not expected_set else 0.0

        intersection = called_set & expected_set
        return len(intersection) / len(called_set)

    def recall(self, called_tools: List[str], expected_tools: List[str]) -> float:
        """Compute only the recall score."""
        called_set: set = set(called_tools or [])
        expected_set: set = set(expected_tools or [])

        if not expected_set:
            return 1.0

        intersection = called_set & expected_set
        return len(intersection) / len(expected_set)
