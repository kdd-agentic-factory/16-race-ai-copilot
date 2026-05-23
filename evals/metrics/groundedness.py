"""Groundedness metric — measures claim-level support in evidence."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union


class GroundednessMetric:
    """Evaluates how well an answer is grounded in provided evidence.

    The metric works by:
    1. Splitting the answer into individual claims (sentences).
    2. Extracting claim-significant tokens (numbers, proper nouns,
       important keywords) from each claim.
    3. Checking if each claim's significant tokens appear in the
       evidence packet (sources + raw data).
    4. Returning the ratio of supported claims to total claims.
    """

    def __init__(self, min_token_overlap: int = 1):
        """Initialise the metric.

        Args:
            min_token_overlap: Minimum number of significant tokens that
                must match between a claim and the evidence for the claim
                to count as supported. Defaults to 1.
        """
        self.min_token_overlap = min_token_overlap

    def evaluate(
        self,
        answer: str,
        evidence_packet: Any,
    ) -> float:
        """Compute groundedness score for an answer against evidence.

        Args:
            answer: The generated response text.
            evidence_packet: An ``EvidencePacket`` (from schemas), a dict
                with ``sources`` and ``raw_data`` keys, a list of
                evidence items, or ``None``.

        Returns:
            A float between 0.0 (no claims supported) and 1.0 (all
            claims supported). Returns 1.0 if there are no claims.
        """
        if not answer or not answer.strip():
            return 1.0

        evidence_text = self._flatten_evidence(evidence_packet)

        if not evidence_text:
            # No evidence available — groundedness is 0
            return 0.0

        claims = self._split_claims(answer)
        if not claims:
            return 1.0

        supported_count = 0
        for claim in claims:
            if self._is_claim_supported(claim, evidence_text):
                supported_count += 1

        return supported_count / len(claims)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flatten_evidence(self, evidence_packet: Any) -> str:
        """Convert an evidence packet to a flat searchable string."""
        if evidence_packet is None:
            return ""

        # duck-type EvidencePacket (has .sources and .raw_data)
        if hasattr(evidence_packet, "sources") and hasattr(
            evidence_packet, "raw_data"
        ):
            texts: List[str] = []

            for src in evidence_packet.sources:
                snippet = getattr(src, "snippet", str(src))
                title = getattr(src, "title", "")
                texts.append(f"{title}: {snippet}")

            texts.extend(evidence_packet.raw_data)
            return "\n".join(texts)

        # list of dicts
        if isinstance(evidence_packet, list):
            parts: List[str] = []
            for item in evidence_packet:
                if isinstance(item, dict):
                    parts.append(
                        item.get("snippet", item.get("text", str(item)))
                    )
                else:
                    parts.append(str(item))
            return "\n".join(parts)

        # plain dict
        if isinstance(evidence_packet, dict):
            sources = evidence_packet.get("sources", [])
            raw = evidence_packet.get("raw_data", [])
            parts2: List[str] = []
            for s in sources:
                parts2.append(
                    s.get("snippet", s.get("text", str(s)))
                    if isinstance(s, dict)
                    else str(s)
                )
            parts2.extend(raw)
            return "\n".join(parts2)

        return str(evidence_packet)

    def _split_claims(self, answer: str) -> List[str]:
        """Split the answer into individual claim sentences."""
        # Split on sentence boundaries
        raw_sentences = re.split(r"(?<=[.!?])\s+", answer.strip())

        claims: List[str] = []
        for s in raw_sentences:
            cleaned = s.strip()
            if cleaned and len(cleaned) > 5:
                claims.append(cleaned)
        return claims

    def _extract_significant_tokens(self, text: str) -> List[str]:
        """Extract tokens that carry factual weight.

        This includes:
        - Numbers (ints, floats, percentages)
        - Capitalised words (proper nouns, units like °C, PSI)
        - Words longer than 4 characters (likely meaningful)
        """
        text_lower = text.lower()
        tokens: List[str] = []

        # Numbers and percentages
        tokens.extend(re.findall(r"\b\d+\.?\d*\s*%?\b", text))

        # Capitalised words (proper nouns, units)
        tokens.extend(re.findall(r"\b[A-Z][a-z]+\b", text))

        # Units with numbers (e.g. 98°C, 3.2°, 22 PSI)
        tokens.extend(re.findall(r"\b\d+\.?\d*\s*°[CF]?\b", text))
        tokens.extend(re.findall(r"\b\d+\s*PSI\b", text))

        # Significant lowercase words (>4 chars)
        for word in re.findall(r"\b[a-z]{5,}\b", text_lower):
            tokens.append(word)

        return tokens

    def _is_claim_supported(self, claim: str, evidence_text: str) -> bool:
        """Check if a single claim is supported by the evidence.

        A claim is supported if at least ``min_token_overlap`` of its
        significant tokens appear in the evidence text.
        """
        tokens = self._extract_significant_tokens(claim)
        if not tokens:
            # The claim has no factual tokens — treat as opinion, count
            # as supported.
            return True

        evidence_lower = evidence_text.lower()
        matches = 0
        for token in tokens:
            if token.lower() in evidence_lower:
                matches += 1
                if matches >= self.min_token_overlap:
                    return True

        return False
