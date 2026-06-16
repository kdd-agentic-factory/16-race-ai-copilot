"""Legacy prototype entrypoint shim.

The canonical backend now lives in ``backend/src/race_ai_copilot``.
This module re-exports that app so old ``uvicorn app.main:app``
invocations keep working while the prototype surface is frozen.
"""

from pathlib import Path
import sys

_BACKEND_SRC = Path(__file__).resolve().parents[3] / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from race_ai_copilot.main import app

__all__ = ["app"]
