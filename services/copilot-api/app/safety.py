"""Legacy prototype approval helpers shim.

Deprecated in favor of :mod:`race_ai_copilot.services.legacy_surface_service`.
"""

from race_ai_copilot.services.legacy_surface_service import LegacySurfaceService

from ._compat import warn_deprecated

warn_deprecated("app.safety", "race_ai_copilot.services.legacy_surface_service")

_LEGACY_SURFACE_SERVICE = LegacySurfaceService()

requires_human_approval = _LEGACY_SURFACE_SERVICE.requires_human_approval
approval_status = _LEGACY_SURFACE_SERVICE.approval_status

__all__ = ["requires_human_approval", "approval_status"]
