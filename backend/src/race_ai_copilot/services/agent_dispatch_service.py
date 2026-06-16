from __future__ import annotations

from ..contracts import AgentDispatchPlan, RequestContext, TypedMCPToolCall


class AgentDispatchService:
    """Choose specialized read-only agents for grounded race workflows."""

    def dispatch(self, query: str, context: RequestContext | None = None) -> AgentDispatchPlan:
        context = context or RequestContext.from_values(tenant_id="tenant-default")
        workflow, agent_name, tool_name = self._classify(query)
        approval_required = workflow in {"setup", "parts", "simulation"}

        tool_call = TypedMCPToolCall.from_context(
            tool_name=tool_name,
            arguments={
                "query": query,
                "workflow": workflow,
                "tenant_id": context.tenant_id,
            },
            context=context,
            audit_source="agent_dispatch",
            approval_required=approval_required,
        )

        return AgentDispatchPlan(
            workflow=workflow,
            agent_name=agent_name,
            tool_calls=[tool_call],
        )

    def _classify(self, query: str) -> tuple[str, str, str]:
        text = query.lower()
        if any(token in text for token in ("setup", "wing", "suspension", "rebound", "damper")):
            return "setup", "setup_agent", "setup.recommend"
        if any(token in text for token in ("part", "component", "cooling", "brake", "design")):
            return "parts", "parts_agent", "parts.cad_review"
        if any(token in text for token in ("simulate", "simulation", "forecast", "predict")):
            return "simulation", "simulation_agent", "simulation.run"
        if any(token in text for token in ("report", "summary", "crew chief", "brief")):
            return "reporting", "reporting_agent", "reporting.session_summary"
        if any(token in text for token in ("telemetry", "delta", "stint", "lap")):
            return "telemetry", "telemetry_agent", "telemetry.compare"
        return "telemetry", "telemetry_agent", "telemetry.compare"
