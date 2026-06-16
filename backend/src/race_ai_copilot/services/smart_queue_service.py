"""Deterministic smart queue ranking for ticket triage."""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import RequestContext
from ..models.ticketing import (
    LifecycleState,
    RankedTicket,
    SlaStatus,
    SeverityLevel,
    SmartQueueRequest,
    SmartQueueResponse,
    TicketInput,
)


@dataclass(frozen=True)
class SlaLifecycleAssessment:
    status: SlaStatus
    reasons: list[str]


class SlaLifecycleService:
    """Classify SLA and lifecycle state in an explainable way."""

    def assess(self, ticket: TicketInput) -> SlaLifecycleAssessment:
        reasons: list[str] = []

        if ticket.lifecycle_state in {LifecycleState.resolved, LifecycleState.closed}:
            reasons.append("Ticket is closed or resolved, so it is excluded from the active queue.")
            return SlaLifecycleAssessment(status=SlaStatus.paused, reasons=reasons)

        if ticket.sla_remaining_minutes is None:
            reasons.append("No SLA timer provided; lifecycle state is the main signal.")
            status = SlaStatus.healthy
        elif ticket.sla_remaining_minutes < 0:
            reasons.append(f"SLA breached by {abs(ticket.sla_remaining_minutes)} minutes.")
            status = SlaStatus.breached
        elif ticket.sla_remaining_minutes <= 60:
            reasons.append(f"SLA is due in {ticket.sla_remaining_minutes} minutes.")
            status = SlaStatus.at_risk
        else:
            reasons.append(f"SLA has {ticket.sla_remaining_minutes} minutes remaining.")
            status = SlaStatus.healthy

        lifecycle_messages = {
            LifecycleState.new: "Ticket is new and should be triaged.",
            LifecycleState.in_progress: "Ticket is actively being worked.",
            LifecycleState.waiting_customer: "Ticket is waiting on customer input.",
            LifecycleState.waiting_third_party: "Ticket is waiting on a third-party dependency.",
        }
        message = lifecycle_messages.get(ticket.lifecycle_state)
        if message:
            reasons.append(message)

        if ticket.blocked:
            reasons.append("Ticket is marked blocked, which slows resolution.")

        return SlaLifecycleAssessment(status=status, reasons=reasons)


@dataclass(frozen=True)
class QueueScoreResult:
    score: float
    band: str
    reasons: list[str]


class QueueStrategyService:
    """Assign a deterministic, explainable score to a ticket."""

    _SEVERITY_WEIGHTS = {
        SeverityLevel.low: 10,
        SeverityLevel.medium: 20,
        SeverityLevel.high: 32,
        SeverityLevel.critical: 44,
    }
    _TIER_WEIGHTS = {
        "standard": 0,
        "premium": 6,
        "enterprise": 12,
    }
    _QUEUE_WEIGHTS = {
        "general": 0,
        "support": 6,
        "incident": 14,
        "vip": 18,
        "backlog": -4,
    }
    _LIFECYCLE_WEIGHTS = {
        LifecycleState.new: 5,
        LifecycleState.in_progress: 12,
        LifecycleState.waiting_customer: -3,
        LifecycleState.waiting_third_party: 2,
        LifecycleState.resolved: -100,
        LifecycleState.closed: -100,
    }

    def score(self, ticket: TicketInput, assessment: SlaLifecycleAssessment) -> QueueScoreResult:
        if assessment.status is SlaStatus.paused:
            return QueueScoreResult(score=-100.0, band="paused", reasons=assessment.reasons)

        score = 0.0
        reasons: list[str] = []

        severity_weight = self._SEVERITY_WEIGHTS.get(ticket.severity, 20)
        score += severity_weight
        reasons.append(f"Severity {ticket.severity.value} adds {severity_weight} points.")

        tier_weight = self._TIER_WEIGHTS.get(ticket.customer_tier.lower(), 0)
        if tier_weight:
            score += tier_weight
            reasons.append(f"Customer tier {ticket.customer_tier} adds {tier_weight} points.")

        queue_weight = self._QUEUE_WEIGHTS.get(ticket.queue.lower(), 0)
        if queue_weight:
            score += queue_weight
            reasons.append(f"Queue {ticket.queue} adds {queue_weight} points.")

        lifecycle_weight = self._LIFECYCLE_WEIGHTS.get(ticket.lifecycle_state, 0)
        if lifecycle_weight:
            score += lifecycle_weight
            reasons.append(f"Lifecycle state {ticket.lifecycle_state.value} adds {lifecycle_weight} points.")

        age_weight = min(ticket.age_hours // 4, 15)
        if age_weight:
            score += float(age_weight)
            reasons.append(f"Age adds {age_weight} points after {ticket.age_hours} hours.")

        if ticket.blocked:
            score += 8
            reasons.append("Blocked work adds 8 points.")

        if assessment.status is SlaStatus.breached:
            score += 40
            reasons.append("SLA breach adds 40 points.")
        elif assessment.status is SlaStatus.at_risk:
            score += 22
            reasons.append("SLA at risk adds 22 points.")
        elif assessment.status is SlaStatus.healthy:
            score += 4
            reasons.append("Healthy SLA keeps a small baseline triage weight.")

        if score >= 80:
            band = "critical"
        elif score >= 55:
            band = "high"
        elif score >= 30:
            band = "medium"
        else:
            band = "low"

        return QueueScoreResult(score=round(score, 1), band=band, reasons=reasons + assessment.reasons)


class SmartQueueService:
    """Rank tickets into a prioritized, explainable queue."""

    def __init__(self, sla_service: SlaLifecycleService | None = None, strategy_service: QueueStrategyService | None = None):
        self.sla_service = sla_service or SlaLifecycleService()
        self.strategy_service = strategy_service or QueueStrategyService()

    def rank(self, request: SmartQueueRequest, request_context: RequestContext | None = None) -> SmartQueueResponse:
        request_context = request_context or RequestContext.from_values(tenant_id="tenant-default")
        active_tickets = [
            ticket
            for ticket in request.tickets
            if ticket.lifecycle_state not in {LifecycleState.resolved, LifecycleState.closed}
            and ticket.tenant_id in (None, request_context.tenant_id)
        ]

        ranked: list[RankedTicket] = []
        for ticket in active_tickets:
            assessment = self.sla_service.assess(ticket)
            score_result = self.strategy_service.score(ticket, assessment)
            ranked.append(
                RankedTicket(
                    ticket=ticket,
                    rank=0,
                    score=score_result.score,
                    band=score_result.band,
                    sla_status=assessment.status,
                    reasons=score_result.reasons,
                    recommended_action=self._recommended_action(ticket, assessment.status),
                )
            )

        ranked.sort(
            key=lambda item: (
                self._sla_priority(item.sla_status),
                item.score,
                self._severity_rank(item.ticket.severity),
                item.ticket.age_hours,
            ),
            reverse=True,
        )

        max_items = request.max_items or len(ranked)
        ranked = ranked[:max_items]

        for index, item in enumerate(ranked, start=1):
            item.rank = index

        summary = self._build_summary(request.queue_name, request.tickets, ranked)
        return SmartQueueResponse(
            queue_name=request.queue_name,
            ranked_tickets=ranked,
            summary=summary,
            total_tickets=len(request.tickets),
            active_tickets=len(active_tickets),
        )

    def _severity_rank(self, severity: SeverityLevel) -> int:
        return {
            SeverityLevel.low: 1,
            SeverityLevel.medium: 2,
            SeverityLevel.high: 3,
            SeverityLevel.critical: 4,
        }.get(severity, 2)

    def _sla_priority(self, status: SlaStatus) -> int:
        return {
            SlaStatus.breached: 3,
            SlaStatus.at_risk: 2,
            SlaStatus.healthy: 1,
            SlaStatus.paused: 0,
        }.get(status, 1)

    def _recommended_action(self, ticket: TicketInput, status: SlaStatus) -> str:
        if status is SlaStatus.breached:
            return "Escalate immediately and assign an on-call owner."
        if status is SlaStatus.at_risk:
            return "Handle next and keep the SLA clock visible."
        if ticket.lifecycle_state is LifecycleState.waiting_customer:
            return "Send a customer follow-up for the missing information."
        if ticket.lifecycle_state is LifecycleState.waiting_third_party:
            return "Chase the third-party dependency and keep the ticket warm."
        if ticket.lifecycle_state is LifecycleState.new:
            return "Triage now and assign an owner."
        return "Continue active work and capture the next diagnostic step."

    def _build_summary(self, queue_name: str | None, tickets: list[TicketInput], ranked: list[RankedTicket]) -> str:
        breached = sum(1 for ticket in ranked if ticket.sla_status is SlaStatus.breached)
        at_risk = sum(1 for ticket in ranked if ticket.sla_status is SlaStatus.at_risk)
        queue_label = queue_name or "active"
        return (
            f"Ranked {len(ranked)} active tickets for {queue_label} queue: "
            f"{breached} breached, {at_risk} at risk, out of {len(tickets)} total."
        )
