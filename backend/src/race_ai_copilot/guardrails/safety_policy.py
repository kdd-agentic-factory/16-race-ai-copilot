from typing import Any, Dict, List, Optional

from .approval_guard import ApprovalGuard
from .evidence_required_guard import EvidenceRequiredGuard
from .race_decision_guard import RaceDecisionGuard
from ..contracts import TypedMCPToolCall


CRITICAL_TOOL_MARKERS = (
    "setup.",
    "parts.",
    "simulation.",
    "reporting.publish",
    "orchestrator.execute",
    "mcp_gateway.execute",
    "write",
    "apply",
    "change",
    "delete",
    "create",
)


class SafetyPolicy:
    """Integrates all guards into a single safety-check pipeline.

    Provides a unified ``check()`` method that runs:
    1. ``ApprovalGuard`` — scans for critical keywords.
    2. ``EvidenceRequiredGuard`` — validates grounding.
    3. ``RaceDecisionGuard`` — sanitises forbidden phrases.

    Returns a compiled safety report with individual results.
    """

    def __init__(
        self,
        approval_guard: Optional[ApprovalGuard] = None,
        evidence_guard: Optional[EvidenceRequiredGuard] = None,
        decision_guard: Optional[RaceDecisionGuard] = None,
    ):
        self.approval_guard = approval_guard or ApprovalGuard()
        self.evidence_guard = evidence_guard or EvidenceRequiredGuard()
        self.decision_guard = decision_guard or RaceDecisionGuard()

    def check(
        self,
        message: str,
        recommendations: List[Any],
        answer: str = "",
        evidence: Optional[Any] = None,
        require_evidence: bool = True,
    ) -> Dict[str, Any]:
        """Run all guards and return a compiled safety report.

        Args:
            message: The original user message.
            recommendations: Structured recommendations (if any).
            answer: The generated response to sanitise.
            evidence: The evidence object used for grounding.
            require_evidence: Whether evidence is mandatory.

        Returns:
            A dict with:
            - ``approval``: result from ``ApprovalGuard.evaluate``.
            - ``evidence_check``: result from ``EvidenceRequiredGuard.evaluate``.
            - ``sanitized_answer``: result from ``RaceDecisionGuard.sanitize``.
            - ``all_passed``: ``True`` when no approval is required AND
              evidence check passes.
        """
        approval_result = self.approval_guard.evaluate(message, recommendations)
        evidence_result = self.evidence_guard.evaluate(
            answer, evidence, require_evidence
        )
        sanitized_answer = self.decision_guard.sanitize(answer)

        all_passed = (
            not approval_result["approval_required"]
            and evidence_result["passed"]
        )

        return {
            "approval": approval_result,
            "evidence_check": evidence_result,
            "sanitized_answer": sanitized_answer,
            "all_passed": all_passed,
        }

    def check_tool_call(
        self,
        tool_call: TypedMCPToolCall,
        approval_granted: bool = False,
    ) -> Dict[str, Any]:
        """Validate whether a typed MCP tool call may proceed."""
        approval_required = self._tool_requires_approval(tool_call)
        blocked = approval_required and not approval_granted
        reason = (
            "Critical MCP tool calls require governed approval before execution."
            if blocked
            else "Tool call is read-only or already governed by approval scope."
        )

        return {
            "approval_required": approval_required,
            "blocked": blocked,
            "reason": reason,
            "tool_call": tool_call.model_dump(),
            "audit": tool_call.audit.model_dump(),
        }

    def _tool_requires_approval(self, tool_call: TypedMCPToolCall) -> bool:
        if tool_call.approval_required or tool_call.audit.critical:
            return True

        tool_name = tool_call.tool_name.lower()
        return any(marker in tool_name for marker in CRITICAL_TOOL_MARKERS)
