"""Evidence coverage metric — measures how much expected evidence is presented."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


class EvidenceCoverageMetric:
    """Evaluates what fraction of the expected evidence was actually
    presented in the copilot's response.

    The metric compares the evidence sources returned in the response
    against a set of expected evidence identifiers or snippets. This
    helps detect when the pipeline fails to retrieve or cite relevant
    evidence.
    """

    def __init__(self, min_score: float = 0.5):
        """Initialise the metric.

        Args:
            min_score: Threshold below which coverage is considered
                poor (used by reporting, not by this metric directly).
        """
        self.min_score = min_score

    def evaluate(
        self,
        response: Any,
        expected_evidence: List[str],
    ) -> float:
        """Compute evidence coverage score.

        Coverage = (number of expected evidence items found in response)
                    / (total number of expected evidence items)

        Args:
            response: A ``ChatResponse`` (from schemas), a dict with an
                ``evidence`` key, or any object with ``evidence``
                attribute containing a list of evidence items.
            expected_evidence: A list of expected evidence identifiers
                or content snippets that should be present in the
                response's evidence list.

        Returns:
            A float between 0.0 (none of the expected evidence was
            presented) and 1.0 (all expected evidence was presented).
            Returns 1.0 if expected_evidence is empty.
        """
        if not expected_evidence:
            return 1.0

        presented_snippets = self._extract_presented_text(response)

        if not presented_snippets:
            return 0.0

        # Count how many expected items are covered by at least one
        # presented snippet
        matched = 0
        for expected in expected_evidence:
            expected_lower = expected.lower().strip()
            if not expected_lower:
                matched += 1
                continue

            # Check if the expected text (or a significant part of it)
            # appears in any presented snippet
            for snippet in presented_snippets:
                if self._text_matches(expected_lower, snippet.lower()):
                    matched += 1
                    break

        return matched / len(expected_evidence)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_presented_text(
        self, response: Any
    ) -> List[str]:
        """Extract all evidence snippet text from a response object."""
        evidence_items = self._get_evidence_list(response)
        snippets: List[str] = []

        for item in evidence_items:
            if isinstance(item, dict):
                text = (
                    item.get("snippet")
                    or item.get("text")
                    or item.get("summary")
                    or str(item)
                )
                snippets.append(text)
            elif hasattr(item, "snippet"):
                snippets.append(getattr(item, "snippet", ""))
            elif hasattr(item, "summary"):
                snippets.append(getattr(item, "summary", ""))
            else:
                snippets.append(str(item))

        return snippets

    def _get_evidence_list(self, response: Any) -> List[Any]:
        """Get the evidence list from a response object regardless of
        its shape."""
        # ChatResponse (pydantic model with .evidence attribute)
        if hasattr(response, "evidence"):
            ev = response.evidence
            if isinstance(ev, list):
                return ev
            if hasattr(ev, "sources"):
                return ev.sources
            return []

        # Dict with an evidence key
        if isinstance(response, dict):
            ev = response.get("evidence", [])
            if isinstance(ev, list):
                return ev
            return []

        return []

    def _text_matches(
        self, expected: str, actual: str
    ) -> bool:
        """Check if expected text appears in the actual snippet.

        Returns True if:
        - The expected text is a substring of the actual text, OR
        - At least 70% of the expected words appear in the actual text
        """
        if not expected or not actual:
            return False

        if expected in actual:
            return True

        expected_words: Set[str] = set(expected.split())
        actual_words: Set[str] = set(actual.split())

        if not expected_words:
            return True

        overlap = expected_words & actual_words
        return len(overlap) / len(expected_words) >= 0.7
