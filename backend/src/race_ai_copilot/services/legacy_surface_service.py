"""Compatibility surface for the absorbed prototype endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ..models.legacy import (
    ChatRequest,
    CopilotResponse,
    CrewChiefReportRequest,
    Evidence,
    EvidenceType,
    PatternAnalysisRequest,
    Recommendation,
    RecommendationType,
    RaceCommandCenterChatRequest,
    RiskLevel,
    SetupRecommendationRequest,
    TelemetryAnalysisRequest,
    ToolCall,
    ToolCallRequest,
    ToolStatus,
)


@dataclass(frozen=True)
class LegacyIntent:
    name: str
    tools: list[str]
    approval_required: bool = False


class LegacySurfaceService:
    """Replicate the legacy prototype behavior on top of canonical code."""

    def build_health(self, default_model: str) -> dict[str, str]:
        return {
            "status": "ok",
            "default_model": default_model,
            "version": "0.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def build_chat_response(self, request: ChatRequest) -> CopilotResponse:
        intent = self.classify_intent(request.message)
        needs_approval = intent.approval_required or self.requires_human_approval(request.message)
        evidence = [
            Evidence(
                source="rag-cag:pending",
                type=EvidenceType.document,
                confidence=0.0,
                summary="Evidence retrieval is proposed. No telemetry evidence has been fabricated.",
            )
        ]
        tool_calls = [
            ToolCall(
                tool=tool,
                status=ToolStatus.proposed,
                approval_required=needs_approval and tool.startswith("orchestrator"),
                arguments={"intent": intent.name, "role": request.role},
            )
            for tool in intent.tools
        ]
        recommendations: list[Recommendation] = []
        if intent.name == "setup_recommendation":
            recommendations.append(
                Recommendation(
                    type=RecommendationType.setup_change,
                    summary="Propose setup hypotheses only after telemetry, tire, and session evidence are retrieved.",
                    risk=RiskLevel.high,
                    approval_required=True,
                    evidence_refs=["rag-cag:pending"],
                )
            )
        if intent.name == "part_design":
            recommendations.append(
                Recommendation(
                    type=RecommendationType.part_design,
                    summary="Propose circuit-specific part concepts only after telemetry, thermal, packaging, and rules evidence are retrieved.",
                    risk=RiskLevel.high,
                    approval_required=True,
                    evidence_refs=["rag-cag:pending"],
                )
            )

        return CopilotResponse(
            message=(
                "Direct answer: I can help with this request, but I need grounded evidence before making an operational claim.\n\n"
                f"Intent: {intent.name}.\n"
                "Evidence: retrieval has been proposed through the platform integrations.\n"
                "Interpretation: no telemetry fact is asserted until RAG/CAG, telemetry, or session tools return data.\n"
                "Recommended action: review the proposed tool calls and approve any critical setup or operational workflow.\n"
                f"Approval status: {self.approval_status(request.message)}."
            ),
            evidence=evidence,
            tool_calls=tool_calls,
            recommendations=recommendations,
            approval_status="required" if needs_approval else "not_required",
            next_step="Route proposed calls through MCP Gateway and Agent Orchestrator.",
        )

    def stream_chat_response(self, response: CopilotResponse):
        for line in response.message.splitlines():
            yield f"data: {line}\n\n"
        yield "event: done\ndata: [DONE]\n\n"

    def build_command_center_response(self, request: RaceCommandCenterChatRequest) -> CopilotResponse:
        response = self.build_chat_response(ChatRequest(message=request.query, role=request.user_role, history=request.history))
        intent = self.classify_intent(request.query)
        command_center_context = {
            "active_session_id": request.active_session_id,
            "circuit": request.circuit,
            "stint_id": request.stint_id,
            "base_setup_id": request.base_setup_id,
            "proposed_setup_id": request.proposed_setup_id,
            "vehicle_context": request.vehicle_context,
            "context": request.context,
        }
        response.evidence.insert(
            0,
            Evidence(
                source="race-command-center:context",
                type=EvidenceType.session,
                confidence=0.0,
                summary="Command Center context was received, but telemetry, setup, and session evidence must be fetched before claims are made.",
            ),
        )
        route_calls = [
            ToolCall(
                tool="race_command_center.context.read",
                status=ToolStatus.proposed,
                arguments=command_center_context,
            ),
            ToolCall(
                tool="rag_cag.retrieve",
                status=ToolStatus.proposed,
                arguments={"intent": intent.name, "query": request.query, "circuit": request.circuit},
            ),
            ToolCall(
                tool="mcp_gateway.dispatch",
                status=ToolStatus.proposed,
                arguments={"intent": intent.name, "downstream_tools": intent.tools},
            ),
            ToolCall(
                tool="agent_orchestrator.plan",
                status=ToolStatus.proposed,
                approval_required=intent.approval_required,
                arguments={"intent": intent.name, "approval_gate": intent.approval_required},
            ),
        ]
        response.tool_calls = route_calls + response.tool_calls
        response.next_step = (
            "Race Command Center should submit the proposed route through the canonical backend; "
            "the copilot will request evidence through RAG/CAG, MCP Gateway, Agent Orchestrator, "
            "and Race Command Center APIs before returning operational claims."
        )
        return response

    def call_tool(self, request: ToolCallRequest) -> CopilotResponse:
        blocked = request.execute and request.approval_token is None
        status = ToolStatus.blocked if blocked else ToolStatus.proposed
        return CopilotResponse(
            message="Tool execution is blocked until routed through approval, or proposed for orchestration.",
            tool_calls=[
                ToolCall(
                    tool=request.tool,
                    status=status,
                    approval_required=blocked,
                    arguments=request.arguments,
                )
            ],
            approval_status="blocked" if blocked else "not_required",
            next_step="Send this tool call to MCP Gateway or Agent Orchestrator.",
        )

    def build_setup_recommendation(self, request: SetupRecommendationRequest) -> CopilotResponse:
        risk = RiskLevel.high if request.track_temperature_c is not None and request.track_temperature_c >= 40 else RiskLevel.medium
        symptom_text = ", ".join(request.symptoms) if request.symptoms else "no explicit symptoms provided"
        return CopilotResponse(
            message=(
                "Direct answer: for setup work, the copilot proposes evidence-gated hypotheses rather than executing changes.\n"
                f"Interpretation: circuit={request.circuit_type}, track_temperature_c={request.track_temperature_c}, symptoms={symptom_text}.\n"
                "Recommended action: retrieve comparable sessions, tire degradation curves, brake temperatures, and balance traces before approving changes."
            ),
            evidence=[
                Evidence(
                    source="telemetry:required",
                    type=EvidenceType.telemetry,
                    confidence=0.0,
                    summary="Telemetry evidence must be fetched before changing setup.",
                )
            ],
            tool_calls=[
                ToolCall(tool="telemetry.compare", status=ToolStatus.proposed, approval_required=False),
                ToolCall(tool="orchestrator.request_human_approval", status=ToolStatus.proposed, approval_required=True),
            ],
            recommendations=[
                Recommendation(
                    type=RecommendationType.setup_change,
                    summary="Create a setup-change candidate after evidence retrieval, with human approval required.",
                    risk=risk,
                    approval_required=True,
                    evidence_refs=["telemetry:required"],
                )
            ],
            approval_status="required",
            next_step="Fetch telemetry and similar-session evidence, then request approval for any physical setup change.",
        )

    def build_telemetry_analysis(self, request: TelemetryAnalysisRequest) -> CopilotResponse:
        target = request.session_a
        if request.session_b:
            target += f" vs {request.session_b}"
        if request.corner:
            target += f" at {request.corner}"
        return CopilotResponse(
            message=f"Telemetry analysis proposed for {target}. No telemetry evidence is invented by the API stub.",
            evidence=[Evidence(source="race-command-center:telemetry", type=EvidenceType.telemetry, confidence=0.0)],
            tool_calls=[
                ToolCall(
                    tool="telemetry.compare" if request.session_b else "telemetry.analyze",
                    status=ToolStatus.proposed,
                    arguments=request.model_dump(),
                )
            ],
            next_step="Fetch traces from Race Command Center and return evidence-backed deltas.",
        )

    def build_pattern_analysis(self, request: PatternAnalysisRequest) -> CopilotResponse:
        return CopilotResponse(
            message=f"Pattern search proposed across the last {request.lookback_sessions} sessions.",
            evidence=[Evidence(source="qdrant:patterns", type=EvidenceType.pattern, confidence=0.0)],
            tool_calls=[ToolCall(tool="patterns.search", status=ToolStatus.proposed, arguments=request.model_dump())],
            next_step="Query vector and session stores for similar telemetry or document patterns.",
        )

    def build_crew_chief_report(self, request: CrewChiefReportRequest) -> CopilotResponse:
        return CopilotResponse(
            message=f"Crew chief report generation proposed for session {request.session_id}.",
            evidence=[Evidence(source=f"session:{request.session_id}", type=EvidenceType.session, confidence=0.0)],
            tool_calls=[
                ToolCall(tool="reports.crew_chief.generate", status=ToolStatus.proposed, arguments=request.model_dump())
            ],
            next_step="Collect anomalies, setup notes, recommendations, and evidence into the report template.",
        )

    def classify_intent(self, message: str) -> LegacyIntent:
        text = message.lower()
        if any(token in text for token in ["pieza", "diseñ", "disen", "refrigeraci", "freno"]):
            return LegacyIntent("part_design", ["rag.query", "skills.part_design", "orchestrator.approval"], True)
        if any(token in text for token in ["patrones", "patron", "similar", "sesiones anteriores", "spin"]):
            return LegacyIntent("pattern_discovery", ["patterns.search", "rag.query"])
        if any(token in text for token in ["informe", "pre-gp", "pregp", "crew chief", "anomal"]):
            return LegacyIntent("crew_chief_report", ["telemetry.analyze", "rag.query", "reports.generate"])
        if any(token in text for token in ["setup", "rebote", "click", "neum", "degrad", "clasificaci"]):
            return LegacyIntent("setup_recommendation", ["rag.query", "telemetry.analyze", "orchestrator.approval"], True)
        if any(token in text for token in ["fp1", "fp2", "telemet", "curva", "mapa motor", "tanda"]):
            return LegacyIntent("telemetry_analysis", ["telemetry.compare", "rag.query"])
        if any(token in text for token in ["adr", "arquitectura", "kafka", "redpanda"]):
            return LegacyIntent("documentation", ["rag.query", "documentation.generate"])
        return LegacyIntent("general_race_copilot", ["rag.query"])

    def requires_human_approval(self, text: str) -> bool:
        normalized = text.lower()
        return any(term in normalized for term in ["setup", "rebote", "suspensión", "brake bias", "mapa motor", "despliegue", "kubernetes", "github", "producción"])

    def approval_status(self, text: str) -> str:
        return "required" if self.requires_human_approval(text) else "not_required"
