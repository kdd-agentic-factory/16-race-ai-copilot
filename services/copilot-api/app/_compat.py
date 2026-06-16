"""Shared helpers for legacy prototype compatibility shims."""

from __future__ import annotations

import warnings


def warn_deprecated(module_name: str, canonical_target: str) -> None:
    warnings.warn(
        f"{module_name} is deprecated; import from {canonical_target} in the canonical backend instead.",
        DeprecationWarning,
        stacklevel=3,
    )
