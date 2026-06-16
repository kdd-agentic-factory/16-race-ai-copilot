"""Legacy prototype payload shim.

Deprecated in favor of :mod:`race_ai_copilot.models.legacy`.
"""

from race_ai_copilot.models.legacy import *  # noqa: F401,F403

from ._compat import warn_deprecated

warn_deprecated("app.schemas", "race_ai_copilot.models.legacy")
