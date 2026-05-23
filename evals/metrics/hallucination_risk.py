"""Hallucination risk metric — detects claims unsupported by evidence."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class HallucinationRiskMetric:
    """Estimates the risk that an answer contains hallucinated content
    (claims not supported by the provided evidence).

    The metric works by:
    1. Extracting factual claims from the answer (sentences containing
       specific data points: numbers, metrics, named entities).
    2. For each claim, checking if the specific data points it
       references appear in the evidence text.
    3. Claims that reference data *not* found in the evidence are
       flagged as potential hallucinations.
    4. Returns a risk score = (flagged claims) / (total factual claims).

    A high score means the answer is likely making up facts.
    """

    def __init__(self, strictness: float = 0.5):
        """Initialise the metric.

        Args:
            strictness: How strict the matching is (0.0 = very lenient,
                1.0 = very strict). Default 0.5. Higher values make
                the token overlap threshold stricter.
        """
        self.strictness = max(0.0, min(1.0, strictness))

    def evaluate(
        self,
        answer: str,
        evidence: Any,
    ) -> float:
        """Compute the hallucination risk score.

        Args:
            answer: The generated response text.
            evidence: An ``EvidencePacket``, dict, list, or ``None``
                representing the available evidence.

        Returns:
            A float between 0.0 (no hallucination risk — all claims
            are backed by evidence) and 1.0 (high risk — most claims
            are unsupported).
        """
        if not answer or not answer.strip():
            return 0.0

        evidence_text = self._flatten_to_text(evidence)

        if not evidence_text:
            # No evidence at all — any factual claim is a hallucination
            factual_claims = self._extract_factual_claims(answer)
            if not factual_claims:
                return 0.0
            return min(1.0, len(factual_claims) / max(1, len(factual_claims)))

        factual_claims = self._extract_factual_claims(answer)
        if not factual_claims:
            return 0.0

        flagged = 0
        for claim in factual_claims:
            if self._is_hallucinated(claim, evidence_text):
                flagged += 1

        return flagged / len(factual_claims)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flatten_to_text(self, evidence: Any) -> str:
        """Convert any evidence shape into a single searchable string."""
        if evidence is None:
            return ""

        # Duck-type EvidencePacket
        if hasattr(evidence, "sources") and hasattr(evidence, "raw_data"):
            parts: List[str] = []
            for src in evidence.sources:
                snippet = getattr(src, "snippet", str(src))
                title = getattr(src, "title", "")
                parts.append(f"{title}: {snippet}")
            parts.extend(evidence.raw_data)
            return "\n".join(parts)

        # List
        if isinstance(evidence, list):
            texts: List[str] = []
            for item in evidence:
                if isinstance(item, dict):
                    texts.append(
                        item.get("snippet")
                        or item.get("text")
                        or item.get("summary")
                        or str(item)
                    )
                else:
                    texts.append(str(item))
            return "\n".join(texts)

        # Dict
        if isinstance(evidence, dict):
            sources = evidence.get("sources", [])
            raw = evidence.get("raw_data", [])
            parts2: List[str] = []
            for s in sources:
                parts2.append(
                    s.get("snippet", s.get("text", str(s)))
                    if isinstance(s, dict)
                    else str(s)
                )
            parts2.extend(raw)
            return "\n".join(parts2)

        return str(evidence)

    def _extract_factual_claims(self, answer: str) -> List[str]:
        """Extract sentences that appear to make factual assertions.

        A factual assertion is a sentence containing at least one
        number (digit or percentage).
        """
        sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
        factual: List[str] = []

        for s in sentences:
            cleaned = s.strip()
            if not cleaned or len(cleaned) < 10:
                continue
            # Must contain at least one number
            if re.search(r"\d+\.?\d*", cleaned):
                factual.append(cleaned)

        return factual

    def _extract_data_points(self, text: str) -> List[Tuple[str, str]]:
        """Extract (key, value) data points from text.

        Returns a list of tuples like:
        - ("temp", "98°C")
        - ("deg", "0.82s")
        - ("pressure", "22 PSI")
        - ("weight", "3.5 kg")
        """
        data_points: List[Tuple[str, str]] = []

        # Patterns: "number unit" (98°C, 0.82s, 22 PSI, 3.5 kg, 650°C, etc.)
        for match in re.finditer(
            r"(\d+\.?\d*)\s*([°a-zA-Z/%]+\b)", text
        ):
            data_points.append((match.group(2), match.group(0)))

        # Patterns: standalone important numbers with context
        # e.g. "lap 8", "turn 9", "44 laps"
        for match in re.finditer(
            r"\b([a-z]+)\s+(\d+\.?\d*)\b", text.lower()
        ):
            key, value = match.group(1), match.group(0)
            if len(key) >= 2:
                data_points.append((key, value))

        return data_points

    def _is_hallucinated(self, claim: str, evidence_text: str) -> bool:
        """Determine if a single claim is likely hallucinated.

        A claim is flagged as hallucinated if it contains data points
        (numbers, specific values) that do NOT appear in the evidence
        text.
        """
        data_points = self._extract_data_points(claim)
        if not data_points:
            # Opinion / qualitative claim — not flagged
            return False

        evidence_lower = evidence_text.lower()
        unsupported = 0

        for key, value in data_points:
            value_lower = value.lower()
            # Check if the data point exists in evidence
            found = value_lower in evidence_lower

            # Try fuzzy match for close values (lenient at low strictness)
            if not found and self.strictness < 0.3:
                # Check if just the number part appears
                num_match = re.search(r"\d+\.?\d*", value)
                if num_match:
                    number = num_match.group()
                    found = number in evidence_lower

            if not found:
                unsupported += 1

        # Hallucinated if a significant fraction of data points are
        # unsupported
        threshold = 1.0 - self.strictness
        if unsupported / len(data_points) >= threshold:
            return True

        return False
