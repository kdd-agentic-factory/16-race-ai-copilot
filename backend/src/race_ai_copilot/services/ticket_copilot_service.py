"""Heuristic ticket copilot for concise summaries and next actions."""

from __future__ import annotations

from collections import OrderedDict

from ..contracts import RequestContext
from ..models.ticketing import LifecycleState, SlaStatus, SeverityLevel, TicketCopilotResponse, TicketInput
from .smart_queue_service import QueueStrategyService, SlaLifecycleService


class TicketCopilotService:
    """Build a concise, deterministic copilot response for a ticket."""

    _HINT_MAP = OrderedDict(
        [
            ("auth", ["Account access incident", "Password reset follow-up", "SSO/login regression"]),
            ("login", ["Account access incident", "Password reset follow-up", "SSO/login regression"]),
            ("password", ["Password reset follow-up", "Account access incident", "Credential sync issue"]),
            ("billing", ["Invoice dispute", "Payment authorization failure", "Refund workflow"]),
            ("payment", ["Invoice dispute", "Payment authorization failure", "Refund workflow"]),
            ("outage", ["Production incident", "Service degradation", "Monitoring alert triage"]),
            ("incident", ["Production incident", "Incident bridge notes", "Monitoring alert triage"]),
            ("api", ["Integration failure", "Webhook retry issue", "Downstream timeout"]),
            ("timeout", ["Downstream timeout", "Integration failure", "Retry budget exhaustion"]),
            ("slow", ["Performance regression", "Latency spike", "Query tuning"]),
            ("latency", ["Performance regression", "Latency spike", "Query tuning"]),
        ]
    )

    def __init__(self, sla_service: SlaLifecycleService | None = None, strategy_service: QueueStrategyService | None = None):
        self.sla_service = sla_service or SlaLifecycleService()
        self.strategy_service = strategy_service or QueueStrategyService()

    def summarize(
        self,
        ticket: TicketInput,
        queue_context: list[TicketInput] | None = None,
        request_context: RequestContext | None = None,
    ) -> TicketCopilotResponse:
        request_context = request_context or RequestContext.from_values(tenant_id="tenant-default")
        if ticket.tenant_id not in (None, request_context.tenant_id):
            ticket = TicketInput.model_validate({**ticket.model_dump(), "tenant_id": request_context.tenant_id})
        queue_context = [item for item in (queue_context or []) if item.tenant_id in (None, request_context.tenant_id)]
        assessment = self.sla_service.assess(ticket)
        score_result = self.strategy_service.score(ticket, assessment)
        summary = self._build_summary(ticket, assessment.status)
        similar_case_hints = self._build_similar_case_hints(ticket, queue_context)
        recommended_next_actions = self._build_next_actions(ticket, assessment.status)
        escalation_hints = self._build_escalation_hints(ticket, assessment.status)
        confidence = self._confidence(ticket, similar_case_hints, queue_context)

        return TicketCopilotResponse(
            ticket_id=ticket.ticket_id,
            summary=summary,
            similar_case_hints=similar_case_hints,
            recommended_next_actions=recommended_next_actions,
            escalation_hints=escalation_hints,
            confidence=confidence,
            queue_band=score_result.band,
            sla_status=assessment.status,
        )

    def _build_summary(self, ticket: TicketInput, sla_status: SlaStatus) -> str:
        severity = ticket.severity.value.replace("_", " ")
        queue = ticket.queue.replace("_", " ")
        subject = ticket.subject.strip().rstrip(".")
        status_clause = {
            SlaStatus.breached: "SLA is breached",
            SlaStatus.at_risk: "SLA is at risk",
            SlaStatus.paused: "ticket is paused",
            SlaStatus.healthy: "SLA is stable",
        }[sla_status]

        lifecycle_clause = {
            LifecycleState.new: "new",
            LifecycleState.in_progress: "in progress",
            LifecycleState.waiting_customer: "waiting on the customer",
            LifecycleState.waiting_third_party: "waiting on a third party",
            LifecycleState.resolved: "resolved",
            LifecycleState.closed: "closed",
        }[ticket.lifecycle_state]

        summary = f"{severity.title()} ticket in {queue}: {subject}. {status_clause}; {lifecycle_clause}."
        return self._truncate(summary, 180)

    def _build_similar_case_hints(self, ticket: TicketInput, queue_context: list[TicketInput]) -> list[str]:
        tokens = self._tokenize(ticket.subject, ticket.description, ticket.queue, *ticket.tags)
        hints: list[str] = []
        for token in tokens:
            for key, values in self._HINT_MAP.items():
                if key in token:
                    for value in values:
                        if value not in hints:
                            hints.append(value)
                        if len(hints) == 3:
                            return hints

        if queue_context:
            context_hint = f"Closest past tickets in {queue_context[0].queue} queue"
            hints.append(context_hint)

        if not hints:
            hints.extend([
                "Search the same queue for the nearest historical match",
                "Compare against tickets with the same severity",
            ])

        return hints[:3]

    def _build_next_actions(self, ticket: TicketInput, sla_status: SlaStatus) -> list[str]:
        actions: list[str] = []

        if sla_status is SlaStatus.breached:
            actions.append("Escalate to the on-call owner now.")
        elif sla_status is SlaStatus.at_risk:
            actions.append("Prioritize the ticket before the SLA expires.")

        if ticket.lifecycle_state is LifecycleState.waiting_customer:
            actions.append("Request the missing customer details.")
            actions.append("Set a follow-up reminder.")
        elif ticket.lifecycle_state is LifecycleState.waiting_third_party:
            actions.append("Chase the third-party dependency.")
        elif ticket.lifecycle_state is LifecycleState.new:
            actions.append("Assign an owner and triage the issue.")
        else:
            actions.append("Capture the next diagnostic step in the ticket.")

        if ticket.severity in {SeverityLevel.high, SeverityLevel.critical}:
            actions.append("Pull in a senior agent for review.")

        return self._dedupe(actions)

    def _build_escalation_hints(self, ticket: TicketInput, sla_status: SlaStatus) -> list[str]:
        hints: list[str] = []

        if sla_status is SlaStatus.breached:
            hints.append("Escalate to the on-call owner immediately.")
            hints.append("Notify the incident commander and capture the breach timestamp.")
        elif sla_status is SlaStatus.at_risk:
            hints.append("Warn the assignee before the SLA expires.")
            hints.append("Prepare an escalation path if progress stalls.")

        if ticket.severity is SeverityLevel.critical and sla_status is not SlaStatus.paused:
            hints.append("Pull in a senior reviewer for the escalation decision.")

        return self._dedupe(hints)

    def _confidence(self, ticket: TicketInput, hints: list[str], queue_context: list[TicketInput]) -> float:
        confidence = 0.45
        confidence += 0.1 if ticket.description else 0.05
        confidence += 0.1 if ticket.tags else 0.0
        confidence += 0.1 if hints else 0.0
        confidence += 0.05 if queue_context else 0.0
        confidence += 0.05 if ticket.sla_remaining_minutes is not None else 0.0
        return min(confidence, 0.92)

    def _tokenize(self, *parts: str) -> list[str]:
        tokens: list[str] = []
        for part in parts:
            for token in part.lower().replace("/", " ").replace("-", " ").split():
                cleaned = token.strip(".,:;!?()[]{}")
                if cleaned:
                    tokens.append(cleaned)
        return tokens

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"

    def _dedupe(self, values: list[str]) -> list[str]:
        return list(OrderedDict.fromkeys(values))
