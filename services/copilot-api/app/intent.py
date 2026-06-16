"""Legacy prototype intent shim.

Deprecated in favor of :mod:`race_ai_copilot.services.legacy_surface_service`.
"""

from race_ai_copilot.services.legacy_surface_service import LegacyIntent, LegacySurfaceService

from ._compat import warn_deprecated

warn_deprecated("app.intent", "race_ai_copilot.services.legacy_surface_service")

_LEGACY_SURFACE_SERVICE = LegacySurfaceService()

Intent = LegacyIntent


def classify_intent(message: str) -> Intent:
    return _LEGACY_SURFACE_SERVICE.classify_intent(message)


__all__ = ["Intent", "classify_intent"]
