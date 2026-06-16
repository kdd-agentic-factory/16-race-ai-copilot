"""SLA War Room service for breached and at-risk ticket cohorts."""

from __future__ import annotations

from typing import Any

from ..contracts import ApprovalMetadata, WarRoomRequestEnvelope, WarRoomResponseEnvelope
from ..models.ticketing import LifecycleState, SlaStatus, TicketInput


class SlaWarRoomService:
    """Build an escalation-oriented war room response from ticket cohorts."""

    def route(self, request: WarRoomRequestEnvelope) -> WarRoomResponseEnvelope:
        tickets = [
            ticket
            for ticket in self._normalize_tickets(request.payload.get("tickets", []))
            if ticket.tenant_id in (None, request.context.tenant_id)
        ]
        cohorts = self._split_cohorts(tickets)
        breached = cohorts["breached"]
        at_risk = cohorts["at_risk"]

        escalation_needed = bool(breached or at_risk)
        counts = {name: len(items) for name, items in cohorts.items()}
        metadata = {
            "war_room_id": request.war_room_id,
            "topic": request.topic,
            "participants": request.participants,
            "counts": counts,
            "cohorts": {
                "breached": [ticket.ticket_id for ticket in breached],
                "at_risk": [ticket.ticket_id for ticket in at_risk],
                "healthy": [ticket.ticket_id for ticket in cohorts["healthy"]],
            },
        }

        evidence = [
            {
                "source": "sla-war-room:cohort",
                "type": "ticket_cohort",
                "confidence": 0.0,
                "summary": self._cohort_summary(counts),
            }
        ]
        if escalation_needed:
            evidence.append(
                {
                    "source": "sla-war-room:escalation",
                    "type": "ticket_escalation",
                    "confidence": 0.0,
                    "summary": "Escalation is proposed but not executed; the response remains read-only.",
                }
            )

        next_actions = self._build_next_actions(breached, at_risk, cohorts["healthy"])

        return WarRoomResponseEnvelope(
            context=request.context,
            reporting=request.reporting,
            status="escalation_needed" if escalation_needed else "monitoring",
            next_actions=next_actions,
            evidence=evidence,
            approval=ApprovalMetadata(
                required=escalation_needed,
                granted=False,
                scope=request.context.approval_scope,
                approver_role="crew_chief" if escalation_needed else None,
                reason="War room escalation proposals require human review." if escalation_needed else None,
            ),
            metadata=metadata,
        )

    def _normalize_tickets(self, raw_tickets: list[Any]) -> list[TicketInput]:
        tickets: list[TicketInput] = []
        for raw_ticket in raw_tickets:
            if isinstance(raw_ticket, TicketInput):
                tickets.append(raw_ticket)
            else:
                tickets.append(TicketInput.model_validate(raw_ticket))
        return tickets

    def _split_cohorts(self, tickets: list[TicketInput]) -> dict[str, list[TicketInput]]:
        cohorts = {"breached": [], "at_risk": [], "healthy": []}
        for ticket in tickets:
            status = self._status_for(ticket)
            if status is SlaStatus.breached:
                cohorts["breached"].append(ticket)
            elif status is SlaStatus.at_risk:
                cohorts["at_risk"].append(ticket)
            else:
                cohorts["healthy"].append(ticket)
        return cohorts

    def _status_for(self, ticket: TicketInput) -> SlaStatus:
        if ticket.lifecycle_state in {LifecycleState.resolved, LifecycleState.closed}:
            return SlaStatus.paused
        if ticket.sla_remaining_minutes is None:
            return SlaStatus.healthy
        if ticket.sla_remaining_minutes < 0:
            return SlaStatus.breached
        if ticket.sla_remaining_minutes <= 60:
            return SlaStatus.at_risk
        return SlaStatus.healthy

    def _build_next_actions(self, breached: list[TicketInput], at_risk: list[TicketInput], healthy: list[TicketInput]) -> list[str]:
        actions: list[str] = []
        if breached:
            actions.append("Escalate breached tickets to the on-call owner now.")
            actions.append("Capture the escalation timestamp and assign a commander.")
        if at_risk:
            actions.append("Warn the owners of at-risk tickets before the SLA expires.")
            actions.append("Prepare a follow-up checkpoint for the at-risk cohort.")
        if not breached and not at_risk:
            actions.append("Continue monitoring the healthy cohort and refresh the war room later.")
        if healthy and (breached or at_risk):
            actions.append("Keep the healthy cohort under observation without escalation.")
        return actions

    def _cohort_summary(self, counts: dict[str, int]) -> str:
        return (
            f"War room reviewed {counts['breached']} breached, {counts['at_risk']} at-risk, "
            f"and {counts['healthy']} healthy tickets."
        )
