"""Pydantic models for observability and reporting payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ObservabilitySignal(BaseModel):
    type: str
    severity: Literal["info", "warn", "critical"] = "info"
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class ObservabilityReport(BaseModel):
    tenant_id: str
    report_type: str
    summary: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    signals: list[ObservabilitySignal] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
