"""Shared service interfaces for canonical backend boundaries."""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

from .contracts import CommandCenterRequestEnvelope, CommandCenterResponseEnvelope, RequestContext, WarRoomRequestEnvelope, WarRoomResponseEnvelope


@runtime_checkable
class KnowledgeService(Protocol):
    async def search(
        self,
        query: str,
        context: RequestContext | None = None,
        limit: int = 5,
    ) -> Sequence[dict[str, Any]]: ...


@runtime_checkable
class TemplateService(Protocol):
    def render(
        self,
        template_name: str,
        context: RequestContext | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str: ...


@runtime_checkable
class ToolService(Protocol):
    async def plan(
        self,
        tool_name: str,
        context: RequestContext | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> Sequence[dict[str, Any]]: ...


@runtime_checkable
class ReportingService(Protocol):
    def generate(
        self,
        report_type: str,
        context: RequestContext | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@runtime_checkable
class CommandCenterRoutingService(Protocol):
    def route(
        self,
        request: CommandCenterRequestEnvelope,
    ) -> CommandCenterResponseEnvelope: ...


@runtime_checkable
class WarRoomService(Protocol):
    def route(
        self,
        request: WarRoomRequestEnvelope,
    ) -> WarRoomResponseEnvelope: ...
