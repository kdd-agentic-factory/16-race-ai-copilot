from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.copilot import build_chat_response, build_command_center_response, build_setup_recommendation
from app.schemas import (
    ChatRequest,
    CopilotResponse,
    CrewChiefReportRequest,
    PatternAnalysisRequest,
    RaceCommandCenterChatRequest,
    SetupRecommendationRequest,
    TelemetryAnalysisRequest,
    ToolCallRequest,
    ToolCall,
    ToolStatus,
    Evidence,
    EvidenceType,
)

app = FastAPI(title="Race AI Copilot API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "default_model": settings.default_model}


@app.post("/chat", response_model=CopilotResponse)
def chat(request: ChatRequest) -> CopilotResponse:
    return build_chat_response(request.message, request.role)


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    response = build_chat_response(request.message, request.role)

    def events():
        for line in response.message.splitlines():
            yield f"data: {line}\n\n"
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/integrations/race-command-center/chat", response_model=CopilotResponse)
def race_command_center_chat(request: RaceCommandCenterChatRequest) -> CopilotResponse:
    return build_command_center_response(request)


@app.post("/tools/call", response_model=CopilotResponse)
def call_tool(request: ToolCallRequest) -> CopilotResponse:
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


@app.post("/recommendations/setup", response_model=CopilotResponse)
def setup_recommendation(request: SetupRecommendationRequest) -> CopilotResponse:
    return build_setup_recommendation(request.circuit_type, request.track_temperature_c, request.symptoms)


@app.post("/analysis/telemetry", response_model=CopilotResponse)
def telemetry_analysis(request: TelemetryAnalysisRequest) -> CopilotResponse:
    target = f"{request.session_a}"
    if request.session_b:
        target += f" vs {request.session_b}"
    if request.corner:
        target += f" at {request.corner}"
    return CopilotResponse(
        message=f"Telemetry analysis proposed for {target}. No telemetry evidence is invented by the API stub.",
        evidence=[
            Evidence(source="race-command-center:telemetry", type=EvidenceType.telemetry, confidence=0.0)
        ],
        tool_calls=[
            ToolCall(
                tool="telemetry.compare" if request.session_b else "telemetry.analyze",
                status=ToolStatus.proposed,
                arguments=request.model_dump(),
            )
        ],
        next_step="Fetch traces from Race Command Center and return evidence-backed deltas.",
    )


@app.post("/analysis/patterns", response_model=CopilotResponse)
def pattern_analysis(request: PatternAnalysisRequest) -> CopilotResponse:
    return CopilotResponse(
        message=f"Pattern search proposed across the last {request.lookback_sessions} sessions.",
        evidence=[Evidence(source="qdrant:patterns", type=EvidenceType.pattern, confidence=0.0)],
        tool_calls=[ToolCall(tool="patterns.search", status=ToolStatus.proposed, arguments=request.model_dump())],
        next_step="Query vector and session stores for similar telemetry or document patterns.",
    )


@app.post("/reports/crew-chief", response_model=CopilotResponse)
def crew_chief_report(request: CrewChiefReportRequest) -> CopilotResponse:
    return CopilotResponse(
        message=f"Crew chief report generation proposed for session {request.session_id}.",
        evidence=[
            Evidence(source=f"session:{request.session_id}", type=EvidenceType.session, confidence=0.0)
        ],
        tool_calls=[ToolCall(tool="reports.crew_chief.generate", status=ToolStatus.proposed, arguments=request.model_dump())],
        next_step="Collect anomalies, setup notes, recommendations, and evidence into the report template.",
    )
