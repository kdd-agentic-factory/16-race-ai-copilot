"""Versioned prompt template service for the canonical backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class TemplateDefinition:
    name: str
    version: str
    path: Path
    content: str


class FileTemplateService:
    """Load markdown prompt templates with explicit version metadata."""

    _MANIFEST: dict[str, tuple[str, str]] = {
        "answer_with_evidence": ("v1", "prompts/templates/answer_with_evidence.template.md"),
        "crew_chief_report": ("v1", "prompts/templates/crew_chief_report.template.md"),
        "paper_note": ("v1", "prompts/templates/paper_note.template.md"),
        "telemetry_analysis": ("v1", "prompts/templates/telemetry_analysis.template.md"),
    }

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent

    def get(self, template_name: str, version: str | None = None) -> TemplateDefinition:
        resolved_version, rel_path = self._resolve(template_name, version)
        path = self.base_dir / rel_path
        return TemplateDefinition(
            name=template_name,
            version=resolved_version,
            path=path,
            content=path.read_text(encoding="utf-8"),
        )

    def available_versions(self, template_name: str) -> list[str]:
        if template_name not in self._MANIFEST:
            raise KeyError(f"Unknown template: {template_name}")
        return [self._MANIFEST[template_name][0]]

    def render(
        self,
        template_name: str,
        context: Any | None = None,
        variables: dict[str, Any] | None = None,
        version: str | None = None,
    ) -> str:
        template = self.get(template_name, version=version)
        merged = {
            **(context.model_dump() if hasattr(context, "model_dump") else {}),
            **(variables or {}),
        }
        rendered = self._substitute(template.content, merged)
        return f"<!-- template-version: {template.version} -->\n{rendered}"

    def _resolve(self, template_name: str, version: str | None) -> tuple[str, str]:
        if template_name not in self._MANIFEST:
            raise KeyError(f"Unknown template: {template_name}")
        default_version, rel_path = self._MANIFEST[template_name]
        if version is None or version == default_version:
            return default_version, rel_path
        raise KeyError(f"Template '{template_name}' does not have version '{version}'")

    def _substitute(self, content: str, variables: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            value = variables.get(key, "")
            return str(value)

        return re.sub(r"\{\{\s*([\w\.\-]+)\s*\}\}", replace, content)
