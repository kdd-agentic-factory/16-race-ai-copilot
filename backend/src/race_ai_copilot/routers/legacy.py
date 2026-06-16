"""Legacy prototype routes retained as compatibility shims."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..models.legacy import (
    ChatRequest,
    CopilotResponse,
    CrewChiefReportRequest,
    PatternAnalysisRequest,
    RaceCommandCenterChatRequest,
    SetupRecommendationRequest,
    TelemetryAnalysisRequest,
    ToolCallRequest,
)
from ..services.legacy_surface_service import LegacySurfaceService

router = APIRouter(tags=["legacy-compat"])
_LEGACY_SURFACE_SERVICE = LegacySurfaceService()


async def get_legacy_surface_service() -> LegacySurfaceService:
    return _LEGACY_SURFACE_SERVICE


@router.post("/chat", response_model=CopilotResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
) -> CopilotResponse:
    return service.build_chat_response(request)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
):
    response = service.build_chat_response(request)
    return StreamingResponse(service.stream_chat_response(response), media_type="text/event-stream")


@router.post("/integrations/race-command-center/chat", response_model=CopilotResponse)
async def race_command_center_chat(
    request: RaceCommandCenterChatRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
) -> CopilotResponse:
    return service.build_command_center_response(request)


@router.post("/tools/call", response_model=CopilotResponse)
async def call_tool(
    request: ToolCallRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
) -> CopilotResponse:
    return service.call_tool(request)


@router.post("/recommendations/setup", response_model=CopilotResponse)
async def setup_recommendation(
    request: SetupRecommendationRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
) -> CopilotResponse:
    return service.build_setup_recommendation(request)


@router.post("/analysis/telemetry", response_model=CopilotResponse)
async def telemetry_analysis(
    request: TelemetryAnalysisRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
) -> CopilotResponse:
    return service.build_telemetry_analysis(request)


@router.post("/analysis/patterns", response_model=CopilotResponse)
async def pattern_analysis(
    request: PatternAnalysisRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
) -> CopilotResponse:
    return service.build_pattern_analysis(request)


@router.post("/reports/crew-chief", response_model=CopilotResponse)
async def crew_chief_report(
    request: CrewChiefReportRequest,
    service: Annotated[LegacySurfaceService, Depends(get_legacy_surface_service)],
) -> CopilotResponse:
    return service.build_crew_chief_report(request)
