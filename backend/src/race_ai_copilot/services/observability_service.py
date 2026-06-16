"""Reporting and observability payload generation."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..contracts import RequestContext
from ..models.observability import ObservabilityReport, ObservabilitySignal
from ..models.ticketing import LifecycleState, SlaStatus, TicketInput


class ObservabilityService:
    """Build deterministic reporting payloads for tenant-scoped signals."""

    def sla_health(self, tickets: list[TicketInput | dict[str, Any]], context: RequestContext) -> dict[str, Any]:
        scoped = self._filter_tenant(tickets, context)
        statuses = [self._sla_status(ticket) for ticket in scoped]
        counts = Counter(statuses)
        total = len(scoped)
        breached = counts[SlaStatus.breached]
        at_risk = counts[SlaStatus.at_risk]
        healthy = counts[SlaStatus.healthy]
        score = round((healthy + at_risk * 0.5) / total, 2) if total else 1.0

        report = ObservabilityReport(
            tenant_id=context.tenant_id,
            report_type="sla_health",
            summary=f"Reviewed {total} tickets for SLA health.",
            metrics={
                "total": total,
                "healthy": healthy,
                "at_risk": at_risk,
                "breached": breached,
                "health_score": score,
            },
            signals=self._sla_signals(breached, at_risk),
            recommendations=self._sla_recommendations(breached, at_risk),
            metadata={"tenant_id": context.tenant_id, "scope": context.approval_scope.value},
        )
        return report.model_dump()

    def groundedness(
        self,
        answer: str,
        evidence: list[dict[str, Any]],
        context: RequestContext,
    ) -> dict[str, Any]:
        scoped_evidence = self._filter_records(evidence, context)
        groundedness_score = 1.0 if scoped_evidence else 0.0
        report = ObservabilityReport(
            tenant_id=context.tenant_id,
            report_type="groundedness",
            summary="Measured whether the answer is backed by tenant-scoped evidence.",
            metrics={
                "evidence_count": len(scoped_evidence),
                "groundedness_score": groundedness_score,
                "answer_length": len(answer),
            },
            signals=[
                ObservabilitySignal(
                    type="groundedness",
                    severity="info" if groundedness_score else "warn",
                    summary="Evidence was found for the answer." if groundedness_score else "No tenant-scoped evidence was supplied.",
                    details={"groundedness_score": groundedness_score},
                )
            ],
            recommendations=[
                "Keep the answer evidence-backed." if groundedness_score else "Add grounded citations before recommending action."
            ],
            metadata={"tenant_id": context.tenant_id},
        )
        return report.model_dump()

    def approvals(self, approvals: list[dict[str, Any]], context: RequestContext) -> dict[str, Any]:
        scoped = self._filter_records(approvals, context)
        required = sum(1 for item in scoped if item.get("required"))
        granted = sum(1 for item in scoped if item.get("required") and item.get("granted"))
        blocked = required - granted
        blocked_rate = round(blocked / required, 2) if required else 0.0
        report = ObservabilityReport(
            tenant_id=context.tenant_id,
            report_type="approvals",
            summary=f"Evaluated {len(scoped)} approval events.",
            metrics={
                "required": required,
                "granted": granted,
                "blocked": blocked,
                "blocked_rate": blocked_rate,
            },
            signals=self._approval_signals(blocked_rate),
            recommendations=[
                "Review blocked approval requests before they reach operations." if blocked else "Approval flow is healthy for the tenant."
            ],
            metadata={"tenant_id": context.tenant_id},
        )
        return report.model_dump()

    def improvement_signals(
        self,
        sla_health: dict[str, Any],
        groundedness: dict[str, Any],
        approvals: dict[str, Any],
        context: RequestContext,
    ) -> dict[str, Any]:
        signals: list[ObservabilitySignal] = []
        health_score = float(sla_health.get("metrics", {}).get("health_score", 1.0))
        groundedness_score = float(groundedness.get("metrics", {}).get("groundedness_score", 1.0))
        blocked_rate = float(approvals.get("metrics", {}).get("blocked_rate", 0.0))

        if health_score < 0.8:
            signals.append(ObservabilitySignal(type="sla_health", severity="warn", summary="SLA health is below target.", details={"health_score": health_score}))
        if groundedness_score < 0.8:
            signals.append(ObservabilitySignal(type="groundedness", severity="warn", summary="Groundedness can be improved.", details={"groundedness_score": groundedness_score}))
        if blocked_rate > 0:
            signals.append(ObservabilitySignal(type="approvals", severity="info", summary="There are blocked approval requests to review.", details={"blocked_rate": blocked_rate}))

        if not signals:
            signals.append(ObservabilitySignal(type="improvement", severity="info", summary="No immediate improvement signals detected.", details={}))

        report = ObservabilityReport(
            tenant_id=context.tenant_id,
            report_type="improvement_signals",
            summary="Combined SLA, groundedness, and approval signals for improvement tracking.",
            metrics={
                "health_score": health_score,
                "groundedness_score": groundedness_score,
                "blocked_rate": blocked_rate,
            },
            signals=signals,
            recommendations=[
                "Tighten evidence collection and approval routing for this tenant." if signals else "Maintain current operational controls."
            ],
            metadata={"tenant_id": context.tenant_id},
        )
        return report.model_dump()

    def _filter_tenant(self, items: list[TicketInput | dict[str, Any]], context: RequestContext) -> list[TicketInput]:
        scoped: list[TicketInput] = []
        for item in items:
            ticket = item if isinstance(item, TicketInput) else TicketInput.model_validate(item)
            if ticket.tenant_id in (None, context.tenant_id):
                scoped.append(ticket)
        return scoped

    def _filter_records(self, items: list[dict[str, Any]], context: RequestContext) -> list[dict[str, Any]]:
        return [item for item in items if item.get("tenant_id") in (None, context.tenant_id)]

    def _sla_status(self, ticket: TicketInput) -> SlaStatus:
        if ticket.lifecycle_state in {LifecycleState.resolved, LifecycleState.closed}:
            return SlaStatus.paused
        if ticket.sla_remaining_minutes is None:
            return SlaStatus.healthy
        if ticket.sla_remaining_minutes < 0:
            return SlaStatus.breached
        if ticket.sla_remaining_minutes <= 60:
            return SlaStatus.at_risk
        return SlaStatus.healthy

    def _sla_signals(self, breached: int, at_risk: int) -> list[ObservabilitySignal]:
        signals: list[ObservabilitySignal] = []
        if breached:
            signals.append(ObservabilitySignal(type="sla_breach", severity="critical", summary=f"{breached} tickets are already breached.", details={"breached": breached}))
        if at_risk:
            signals.append(ObservabilitySignal(type="sla_risk", severity="warn", summary=f"{at_risk} tickets are at risk.", details={"at_risk": at_risk}))
        if not signals:
            signals.append(ObservabilitySignal(type="sla_health", severity="info", summary="No SLA risk detected.", details={}))
        return signals

    def _sla_recommendations(self, breached: int, at_risk: int) -> list[str]:
        recommendations: list[str] = []
        if breached:
            recommendations.append("Escalate breached tickets to the on-call owner.")
        if at_risk:
            recommendations.append("Prioritize at-risk tickets before the SLA expires.")
        if not recommendations:
            recommendations.append("Keep monitoring the healthy ticket cohort.")
        return recommendations

    def _approval_signals(self, blocked_rate: float) -> list[ObservabilitySignal]:
        if blocked_rate > 0:
            return [ObservabilitySignal(type="approval_blockage", severity="warn", summary="Some approvals are still blocked.", details={"blocked_rate": blocked_rate})]
        return [ObservabilitySignal(type="approval_flow", severity="info", summary="No approval blockage detected.", details={})]
