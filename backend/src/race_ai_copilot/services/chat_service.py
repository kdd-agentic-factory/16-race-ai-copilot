"""ChatService — the main orchestrator for the chat pipeline.

The service implements the full **Intent → Plan → Evidence → Compose**
cycle defined in the architecture, wrapping it with governance guardrails
before returning the final ``ChatResponse``.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from ..auth_deps import Principal
from ..contracts import RequestContext
from ..clients.mcp_client import MCPClient
from ..clients.rag_cag_client import RAGCAGClient
from ..conversation_store import load_history, save_turn
from ..guardrails.approval_guard import ApprovalGuard
from ..guardrails.evidence_required_guard import EvidenceRequiredGuard
from ..guardrails.race_decision_guard import RaceDecisionGuard
from ..llm.ollama_client import OllamaClient
from ..models.schemas import (
    ChatRequest,
    ChatResponse,
    EvidenceItem,
    Recommendation,
    ToolCallRecord,
)
from ..reasoning.composer import AnswerComposer, PromptBuilder
from ..reasoning.evidence_planner import EvidenceBuilder
from ..reasoning.intent_classifier import IntentClassifier
from ..reasoning.tool_planner import ToolPlanner


def generate_id() -> str:
    """Return a short human-readable unique identifier (12 hex chars)."""
    return uuid.uuid4().hex[:12]


class ChatService:
    """Main orchestrator for the chat pipeline.

    Wires together the reasoning engine (classifier → planner → evidence →
    composer) and applies governance guardrails before returning a response.
    """

    def __init__(
        self,
        llm_client: OllamaClient,
        rag_cag_client: RAGCAGClient,
        mcp_client: MCPClient,
        intent_classifier: Optional[IntentClassifier] = None,
        tool_planner: Optional[ToolPlanner] = None,
        evidence_builder: Optional[EvidenceBuilder] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        answer_composer: Optional[AnswerComposer] = None,
        approval_guard: Optional[ApprovalGuard] = None,
        evidence_guard: Optional[EvidenceRequiredGuard] = None,
        decision_guard: Optional[RaceDecisionGuard] = None,
    ):
        self.llm_client = llm_client
        self.rag_cag_client = rag_cag_client
        self.mcp_client = mcp_client

        # Reasoning components
        self.intent_classifier = intent_classifier or IntentClassifier(llm_client)
        self.tool_planner = tool_planner or ToolPlanner(llm_client)
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.answer_composer = answer_composer or AnswerComposer(llm_client)

        # Guardrails
        self.approval_guard = approval_guard or ApprovalGuard()
        self.evidence_guard = evidence_guard or EvidenceRequiredGuard()
        self.decision_guard = decision_guard or RaceDecisionGuard()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def answer(
        self,
        request: ChatRequest,
        principal: Optional[Principal] = None,
        request_context: RequestContext | None = None,
    ) -> ChatResponse:
        """Execute the full chat pipeline for a single request.

        Parameters
        ----------
        request:
            The incoming chat message and metadata.
        principal:
            The authenticated caller.  When ``None``, approval features are
            disabled (local-dev mode without auth).

        Steps
        -----
        1. Generate unique IDs for the conversation and message.
        2. Classify the user's intent (keyword + LLM fallback).
        3. Retrieve grounding context from the RAG/CAG service.
        4. Plan tool calls based on the classified intent.
        5. **Pre-execution approval check** — evaluate whether the
           message or planned tools require crew-chief approval.
           Tools are blocked when ``approval_required`` is ``True``
           but ``request.approval_granted`` is ``False``.
        6. Execute tools via the MCP client (SKIPPED when blocked).
        7. Build an ``EvidencePacket`` from RAG + MCP results.
        8. Build a grounded prompt for the LLM.
        9. Generate the answer via ``AnswerComposer`` / Ollama.
        10. Sanitise the answer with ``RaceDecisionGuard``.
        11. Validate evidence presence with ``EvidenceRequiredGuard``.
        12. Post-execution approval check — merge with pre-check result.
        13. Assemble and return the final ``ChatResponse``.

        Raises
        ------
        HTTPException 403
            When ``request.approval_granted`` is ``True`` but the
            authenticated principal does not hold a crew-chief-equivalent
            role.
        """
        # ── Step 1: IDs ──────────────────────────────────────────────
        conversation_id = request.conversation_id or generate_id()
        message_id = generate_id()

        # ── Step 1b: Load conversation history from DB ───────────────
        tenant_id = request_context.tenant_id if request_context else "tenant-default"
        history = await load_history(conversation_id, tenant_id=tenant_id, max_turns=10)

        # Persist the incoming user turn immediately
        await save_turn(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
            tenant_id=tenant_id,
            session_id=request.session_id,
        )

        # ── Step 2: Intent classification ────────────────────────────
        intent = await self.intent_classifier.classify(request.message)

        # ── Step 3: Context retrieval (RAG/CAG) ──────────────────────
        rag_results: Optional[Dict[str, Any]] = None
        try:
            rag_results = await self.rag_cag_client.search_context(
                query=request.message,
                top_k=5,
            )
        except Exception:
            # If the RAG/CAG service is unavailable, continue without it
            rag_results = None

        # ── Step 4: Tool planning ────────────────────────────────────
        tool_plan: List[ToolCallRecord] = await self.tool_planner.plan(
            intent=intent,
            query=request.message,
        )

        # ── Step 5: Pre-execution approval check ─────────────────────
        # Evaluate whether the message and/or planned tools require
        # crew-chief approval BEFORE any tool is executed.  This is the
        # critical security gate — without it tools can be invoked
        # without human oversight.
        pre_approval = self.approval_guard.evaluate(
            message=request.message,
            recommendations=[t.tool_name for t in tool_plan],
        )
        approval_required = pre_approval.get("approval_required", False)
        approval_granted = request.approval_granted
        approver_role: Optional[str] = pre_approval.get("approver_role")

        # Role validation: only crew-chief-equivalent roles can grant approval.
        # If the caller lacks the required role, ignore the client-provided flag.
        if approval_granted and principal and not principal.is_crew_chief:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{principal.role}' cannot grant approval for critical "
                    f"actions. This requires a crew-chief-equivalent role "
                    f"(crew_chief, admin, race_engineer, team_principal)."
                ),
            )

        # When approval IS required but has NOT been granted, we skip
        # tool execution entirely.  Only RAG/CAG context is used so
        # the copilot can still produce a preliminary answer without
        # taking any action.
        tools_blocked = approval_required and not approval_granted

        # ── Step 6: Tool execution (gated) ───────────────────────────
        mcp_results: Optional[Dict[str, Any]] = None
        if tool_plan and not tools_blocked:
            accumulated: Dict[str, Any] = {}
            for tool_record in tool_plan:
                try:
                    result = await self.mcp_client.call_tool(
                        tool_name=tool_record.tool_name,
                        payload=tool_record.parameters,
                    )
                    tool_record.result = result
                    accumulated[tool_record.tool_name] = result
                except Exception as exc:
                    tool_record.result = {"error": str(exc)}
            mcp_results = accumulated if accumulated else None

        # ── Step 7: Build evidence packet ────────────────────────────
        evidence_packet = self.evidence_builder.build(
            rag_results=rag_results,
            mcp_results=mcp_results,
        )
        evidence_items: List[EvidenceItem] = evidence_packet.sources
        confidence: float = evidence_packet.groundedness_score

        # ── Step 8: Build grounded prompt ────────────────────────────
        prompt = self.prompt_builder.build_grounded_prompt(
            query=request.message,
            history=history,
            evidence=evidence_packet,
            tool_trace=tool_plan if not tools_blocked else [],
        )

        # ── Step 9: Generate answer ──────────────────────────────────
        raw_answer: str = await self.answer_composer.compose(
            prompt=prompt,
            stream=False,
        )

        # ── Step 10: Sanitize with RaceDecisionGuard ─────────────────
        sanitized_answer: str = self.decision_guard.sanitize(raw_answer)

        # ── Step 11: EvidenceRequiredGuard ───────────────────────────
        evidence_check = self.evidence_guard.evaluate(
            answer=sanitized_answer,
            evidence=evidence_packet,
            require_evidence=request.require_evidence,
        )

        # Gather uncertainty info when evidence check fails
        uncertainty: Optional[str] = None
        if not evidence_check.get("passed", True):
            uncertainty = (
                "The answer could not be fully grounded in available evidence. "
                "Please verify critical information before acting."
            )

        # ── Step 12: Post-execution ApprovalGuard ────────────────────
        # This second pass captures recommendations mentioned in the
        # answer text itself.  The critical gate (tool execution) was
        # already enforced in Step 5 — this pass is purely informational.
        recommendations: List[Recommendation] = self._extract_recommendations(
            sanitized_answer
        )
        post_approval = self.approval_guard.evaluate(
            message=request.message,
            recommendations=recommendations,
        )
        # Merge: if either pre or post says approval is needed, keep it
        approval_required = approval_required or post_approval.get(
            "approval_required", False
        )
        if post_approval.get("approver_role") and not approver_role:
            approver_role = post_approval["approver_role"]

        # Add a notice when tools were blocked
        if tools_blocked:
            blocked_notice = (
                "Tool execution was blocked because this request requires "
                f"{approver_role or 'crew-chief'} approval. "
                "Set approval_granted=True and resubmit to execute."
            )
            if sanitized_answer:
                sanitized_answer += f"\n\n_{blocked_notice}_"
            uncertainty = (
                uncertainty or ""
            ) + f" {blocked_notice}" if uncertainty else blocked_notice

        # ── Step 12b: Persist assistant reply ──────────────────────
        await save_turn(
            conversation_id=conversation_id,
            role="assistant",
            content=sanitized_answer,
            tenant_id=tenant_id,
            session_id=request.session_id,
        )

        # ── Step 13: Build response ──────────────────────────────────
        return ChatResponse(
            conversation_id=conversation_id,
            message_id=message_id,
            answer=sanitized_answer,
            confidence=confidence,
            evidence=evidence_items,
            tool_calls=tool_plan,
            recommendations=recommendations,
            approval_required=approval_required,
            approver_role=approver_role,
            uncertainty=uncertainty,
            next_actions=self._suggest_next_actions(
                intent, {"approval_required": approval_required, "approver_role": approver_role}
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_recommendations(
        self, answer: str
    ) -> List[Recommendation]:
        """Parse structured recommendations from the answer text.

        This is a simple heuristic-based extractor. A production version
        would use an LLM call or a structured output parser.
        """
        recommendations: List[Recommendation] = []
        lines = answer.split("\n")
        for line in lines:
            lower = line.strip().lower()
            if lower.startswith("recommend") or lower.startswith("suggest"):
                recommendations.append(
                    Recommendation(
                        action=line.strip(),
                        rationale="Extracted from answer text",
                    )
                )
        return recommendations

    def _suggest_next_actions(
        self,
        intent: str,
        approval_result: Dict[str, Any],
    ) -> List[str]:
        """Return a list of suggested follow-up actions based on intent."""
        actions: List[str] = []

        if approval_result.get("approval_required"):
            actions.append("Request crew chief approval for the proposed change")

        intent_suggestions = {
            "Telemetry": [
                "Compare with previous session data",
                "Analyze tire degradation trend",
            ],
            "Setup": [
                "Simulate the suggested setup change",
                "Compare with teammate's setup",
            ],
            "Parts": [
                "Check part availability in inventory",
                "Request part for next race weekend",
            ],
            "Simulation": [
                "Run simulation with different fuel loads",
                "Compare with actual lap data",
            ],
        }
        actions.extend(intent_suggestions.get(intent, []))
        return actions
