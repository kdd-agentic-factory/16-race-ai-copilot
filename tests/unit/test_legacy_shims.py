from __future__ import annotations

import importlib
import warnings

from race_ai_copilot.models.legacy import CopilotResponse as CanonicalCopilotResponse
from race_ai_copilot.services.legacy_surface_service import LegacyIntent


def test_legacy_app_modules_emit_explicit_deprecation_warnings_and_reexport_canonical_types():
    module_names = ["app.config", "app.intent", "app.safety", "app.schemas", "app.copilot"]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        modules = [importlib.reload(importlib.import_module(name)) for name in module_names]

    messages = [str(item.message).lower() for item in caught]
    assert any("deprec" in message and "canonical backend" in message for message in messages)

    config_module, intent_module, safety_module, schemas_module, copilot_module = modules

    assert intent_module.Intent is LegacyIntent
    assert schemas_module.CopilotResponse is CanonicalCopilotResponse
    assert copilot_module.CopilotResponse is CanonicalCopilotResponse
    assert callable(config_module.get_settings)
    assert callable(safety_module.requires_human_approval)
    assert callable(safety_module.approval_status)
