"""Legacy prototype copilot shim.

Deprecated in favor of :mod:`race_ai_copilot.services.legacy_surface_service`.
"""

from race_ai_copilot.models.legacy import ChatRequest, CopilotResponse, RaceCommandCenterChatRequest, SetupRecommendationRequest
from race_ai_copilot.services.legacy_surface_service import LegacySurfaceService

from ._compat import warn_deprecated

warn_deprecated("app.copilot", "race_ai_copilot.services.legacy_surface_service")

_LEGACY_SURFACE_SERVICE = LegacySurfaceService()


def build_chat_response(message: str | ChatRequest, role: str = "crew_chief") -> CopilotResponse:
    request = message if isinstance(message, ChatRequest) else ChatRequest(message=message, role=role)
    return _LEGACY_SURFACE_SERVICE.build_chat_response(request)


def build_command_center_response(request: RaceCommandCenterChatRequest) -> CopilotResponse:
    return _LEGACY_SURFACE_SERVICE.build_command_center_response(request)

__all__ = [
    "CopilotResponse",
    "RaceCommandCenterChatRequest",
    "build_chat_response",
    "build_command_center_response",
    "build_setup_recommendation",
]


def build_setup_recommendation(circuit_type: str, track_temperature_c: float | None, symptoms: list[str]) -> CopilotResponse:
    return _LEGACY_SURFACE_SERVICE.build_setup_recommendation(
        SetupRecommendationRequest(
            circuit_type=circuit_type,
            track_temperature_c=track_temperature_c,
            symptoms=symptoms,
        )
    )
