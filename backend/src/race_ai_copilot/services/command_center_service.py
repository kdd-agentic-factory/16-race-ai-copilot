"""Command Center integration service for read-only chat routing."""

from __future__ import annotations

import asyncio
from typing import Any

from ..contracts import (
    ApprovalMetadata,
    CommandCenterRequestEnvelope,
    CommandCenterResponseEnvelope,
    TypedMCPToolCall,
)
from ..guardrails.safety_policy import SafetyPolicy
from .agent_dispatch_service import AgentDispatchService
from .knowledge_service import KnowledgeRetrievalService


class CommandCenterService:
    """Build a read-only, evidence-gated command center response."""

    def __init__(
        self,
        knowledge_service: KnowledgeRetrievalService | None = None,
        agent_dispatch_service: AgentDispatchService | None = None,
        safety_policy: SafetyPolicy | None = None,
    ):
        self.knowledge_service = knowledge_service or KnowledgeRetrievalService()
        self.agent_dispatch_service = agent_dispatch_service or AgentDispatchService()
        self.safety_policy = safety_policy or SafetyPolicy()

    def route(self, request: CommandCenterRequestEnvelope) -> CommandCenterResponseEnvelope:
        intent = self._classify_intent(request.query)
        approval_required = self._requires_approval(request.query)
        knowledge = asyncio.run(
            self.knowledge_service.retrieve(request.query, context=request.context)
        )
        dispatch_plan = self.agent_dispatch_service.dispatch(request.query, context=request.context)
        typed_tool_calls = [
            TypedMCPToolCall.from_context(
                tool_name=call.tool_name,
                arguments=call.arguments,
                context=request.context,
                audit_source=call.audit.source,
                approval_required=call.approval_required,
            )
            for call in dispatch_plan.tool_calls
        ]
        tool_decisions = [
            self.safety_policy.check_tool_call(tool_call, approval_granted=False)
            for tool_call in typed_tool_calls
        ]
        approval_required = approval_required or any(decision["blocked"] for decision in tool_decisions)

        context_payload = {
            "command_center_id": request.command_center_id,
            "query": request.query,
            "vehicle_context": request.vehicle_context,
            "history_turns": len(request.history),
            "context": request.context.model_dump(),
        }

        evidence = [
            {
                "source": "race-command-center:context",
                "type": "session",
                "confidence": 0.0,
                "summary": (
                    "Command Center context was received; no operational claim is made "
                    "without explicit RAG/CAG, MCP, and orchestrator evidence."
                ),
            }
        ]
        evidence.extend(
            {
                "source": citation.source_id,
                "type": "document",
                "confidence": citation.confidence,
                "summary": citation.snippet,
                "tenant_id": citation.tenant_id,
            }
            for citation in knowledge.citations
        )

        tool_calls = [
            {
                "tool": "race_command_center.context.read",
                "status": "proposed",
                "approval_required": False,
                "arguments": context_payload,
            },
            {
                "tool": "rag_cag.retrieve",
                "status": "proposed",
                "approval_required": False,
                "arguments": {
                    "intent": intent,
                    "query": request.query,
                    "command_center_id": request.command_center_id,
                    "tenant_id": request.context.tenant_id,
                    "audit": knowledge.audit,
                },
            },
            {
                "tool": "agent_orchestrator.plan",
                "status": "proposed",
                "approval_required": approval_required,
                "arguments": {
                    "intent": intent,
                    "agent_name": dispatch_plan.agent_name,
                    "workflow": dispatch_plan.workflow,
                    "tool_calls": [call.model_dump() for call in typed_tool_calls],
                    "audit": [decision["audit"] for decision in tool_decisions],
                },
            },
            {
                "tool": "mcp_gateway.dispatch",
                "status": "proposed",
                "approval_required": approval_required,
                "arguments": {
                    "intent": intent,
                    "downstream_tools": self._downstream_tools(intent),
                    "tenant_id": request.context.tenant_id,
                    "audit": [call.audit.model_dump() for call in typed_tool_calls],
                },
            },
        ]

        recommendations = self._build_recommendations(intent, approval_required)

        return CommandCenterResponseEnvelope(
            context=request.context,
            reporting=request.reporting,
            answer=self._build_answer(request.query, intent, approval_required),
            evidence=evidence,
            tool_calls=tool_calls,
            recommendations=recommendations,
            approval=ApprovalMetadata(
                required=approval_required,
                granted=False,
                scope=request.context.approval_scope,
                approver_role="crew_chief" if approval_required else None,
                reason=self._approval_reason(intent) if approval_required else None,
            ),
            next_step=self._build_next_step(approval_required),
        )

    def _classify_intent(self, query: str) -> str:
        text = query.lower()
        if any(token in text for token in ("setup", "wing", "suspension", "brake", "tire pressure", "balance")):
            return "setup_recommendation"
        if any(token in text for token in ("part", "component", "design", "cooling")):
            return "part_design"
        if any(token in text for token in ("telemetry", "degradation", "lap", "delta", "stint")):
            return "telemetry"
        return "command_center_chat"

    def _requires_approval(self, query: str) -> bool:
        text = query.lower()
        return any(token in text for token in ("setup", "wing", "suspension", "brake", "part design", "increase", "decrease"))

    def _downstream_tools(self, intent: str) -> list[str]:
        if intent == "setup_recommendation":
            return ["telemetry.compare", "orchestrator.request_human_approval"]
        if intent == "part_design":
            return ["rag_cag.retrieve", "orchestrator.request_human_approval"]
        if intent == "telemetry":
            return ["telemetry.fetch", "reporting.session_summary"]
        return ["rag_cag.retrieve", "reporting.session_summary"]

    def _build_recommendations(self, intent: str, approval_required: bool) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = [
            {
                "type": "analysis",
                "summary": "Keep the response evidence-gated and read-only until downstream services provide proof.",
                "risk": "low",
                "approval_required": False,
                "evidence_refs": ["race-command-center:context"],
            }
        ]

        if intent == "setup_recommendation":
            recommendations.append(
                {
                    "type": "setup_change",
                    "summary": "Propose setup hypotheses only after telemetry, tire, and session evidence is retrieved.",
                    "risk": "high",
                    "approval_required": True,
                    "evidence_refs": ["race-command-center:context"],
                }
            )
        elif intent == "part_design":
            recommendations.append(
                {
                    "type": "part_design",
                    "summary": "Propose circuit-specific part concepts only after telemetry and packaging evidence are retrieved.",
                    "risk": "high",
                    "approval_required": True,
                    "evidence_refs": ["race-command-center:context"],
                }
            )

        if approval_required:
            recommendations.append(
                {
                    "type": "approval_gate",
                    "summary": "A crew-chief-equivalent approver must review any operational follow-up before execution.",
                    "risk": "high",
                    "approval_required": True,
                    "evidence_refs": ["race-command-center:context"],
                }
            )

        return recommendations

    def _build_answer(self, query: str, intent: str, approval_required: bool) -> str:
        approval_clause = "Approval is required before any operational follow-up." if approval_required else "No operational write is being requested."
        return (
            "Direct answer: I can help with this Command Center request, but I will only return grounded, read-only guidance.\n\n"
            f"Intent: {intent}.\n"
            "Evidence: Command Center context has been accepted and downstream evidence retrieval is proposed.\n"
            "Interpretation: the response stays traceable and does not invent telemetry or session facts.\n"
            f"Recommended action: {approval_clause}\n"
            f"Approval status: {self._approval_status_text(approval_required)}."
        )

    def _build_next_step(self, approval_required: bool) -> str:
        if approval_required:
            return "Submit the proposed route through the governed approval path before any setup or part change is executed."
        return "Use the proposed route to fetch evidence and continue the read-only analysis through governed services; no operational writes are proposed."

    def _approval_reason(self, intent: str) -> str:
        if intent == "setup_recommendation":
            return "Setup recommendations require human approval before execution."
        if intent == "part_design":
            return "Part-design recommendations require human approval before execution."
        return "Operational follow-up requires human approval before execution."

    def _approval_status_text(self, approval_required: bool) -> str:
        return "required" if approval_required else "not_required"
