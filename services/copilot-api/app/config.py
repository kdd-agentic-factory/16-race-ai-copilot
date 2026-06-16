"""Legacy prototype settings shim.

Deprecated in favor of :mod:`race_ai_copilot.config`.
"""

from race_ai_copilot.config import Settings, get_settings

from ._compat import warn_deprecated

warn_deprecated("app.config", "race_ai_copilot.config")

__all__ = ["Settings", "get_settings"]
