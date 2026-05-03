from app.intent import classify_intent
from app.safety import approval_status, requires_human_approval
from app.schemas import (
    CopilotResponse,
    Evidence,
    EvidenceType,
    Recommendation,
    RecommendationType,
    RiskLevel,
    ToolCall,
    ToolStatus,
)


def build_chat_response(message: str, role: str = "crew_chief") -> CopilotResponse:
    intent = classify_intent(message)
    needs_approval = intent.approval_required or requires_human_approval(message)
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
            arguments={"intent": intent.name, "role": role},
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

    return CopilotResponse(
        message=(
            "Direct answer: I can help with this request, but I need grounded evidence before making an operational claim.\n\n"
            f"Intent: {intent.name}.\n"
            "Evidence: retrieval has been proposed through the platform integrations.\n"
            "Interpretation: no telemetry fact is asserted until RAG/CAG, telemetry, or session tools return data.\n"
            "Recommended action: review the proposed tool calls and approve any critical setup or operational workflow.\n"
            f"Approval status: {approval_status(message)}."
        ),
        evidence=evidence,
        tool_calls=tool_calls,
        recommendations=recommendations,
        approval_status="required" if needs_approval else "not_required",
        next_step="Route proposed calls through MCP Gateway and Agent Orchestrator.",
    )


def build_setup_recommendation(circuit_type: str, track_temperature_c: float | None, symptoms: list[str]) -> CopilotResponse:
    risk = RiskLevel.high if track_temperature_c and track_temperature_c >= 40 else RiskLevel.medium
    symptom_text = ", ".join(symptoms) if symptoms else "no explicit symptoms provided"
    return CopilotResponse(
        message=(
            "Direct answer: for setup work, the copilot proposes evidence-gated hypotheses rather than executing changes.\n"
            f"Interpretation: circuit={circuit_type}, track_temperature_c={track_temperature_c}, symptoms={symptom_text}.\n"
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
