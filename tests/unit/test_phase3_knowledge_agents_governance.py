from __future__ import annotations

import pytest

from race_ai_copilot.contracts import ApprovalScope, RequestContext
from race_ai_copilot.clients.rag_cag_client import RAGCAGClient
from race_ai_copilot.services.agent_dispatch_service import AgentDispatchService
from race_ai_copilot.services.knowledge_service import KnowledgeRetrievalService
from race_ai_copilot.guardrails.safety_policy import SafetyPolicy
from race_ai_copilot.contracts import TypedMCPToolCall


class _RagClientSuccess:
    async def search_context(self, query: str, top_k: int = 5):
        return {
            "sources": [
                {
                    "id": "doc-17",
                    "title": "Telemetry session summary",
                    "url": "/docs/session-17.md",
                    "snippet": "Front tyre temperature climbed steadily in stint 3.",
                    "confidence": 0.92,
                }
            ]
        }


class _RagClientFailure:
    async def search_context(self, query: str, top_k: int = 5):
        raise RuntimeError("RAG unavailable")


@pytest.mark.asyncio
async def test_knowledge_service_returns_citations_from_rag_results():
    service = KnowledgeRetrievalService(rag_cag_client=_RagClientSuccess())
    context = RequestContext.from_values(
        tenant_id="tenant-17",
        user_role="crew_chief",
        approval_scope=ApprovalScope.propose,
        request_id="req-17",
        session_id="ses-17",
    )

    result = await service.retrieve("Why did front tyre temps rise?", context=context)

    assert result.fallback_used is False
    assert result.citations[0].source_id == "doc-17"
    assert result.citations[0].tenant_id == "tenant-17"
    assert result.citations[0].request_id == "req-17"


@pytest.mark.asyncio
async def test_knowledge_service_falls_back_when_rag_is_unavailable():
    service = KnowledgeRetrievalService(rag_cag_client=_RagClientFailure())
    context = RequestContext.from_values(
        tenant_id="tenant-17",
        user_role="viewer",
        approval_scope=ApprovalScope.read_only,
    )

    result = await service.retrieve("Summarize the latest telemetry", context=context)

    assert result.fallback_used is True
    assert result.citations[0].source_id == "rag-cag:fallback"
    assert result.citations[0].tenant_id == "tenant-17"
    assert "fallback" in result.citations[0].summary.lower()


@pytest.mark.parametrize(
    ("query", "expected_agent", "expected_tool"),
    [
        ("Analyze telemetry drift from FP2", "telemetry_agent", "telemetry.compare"),
        ("Recommend a setup for high temperature", "setup_agent", "setup.recommend"),
        ("Design a new brake cooling part", "parts_agent", "parts.cad_review"),
        ("Simulate race pace with full fuel", "simulation_agent", "simulation.run"),
        ("Generate a crew chief report", "reporting_agent", "reporting.session_summary"),
    ],
)
def test_agent_dispatch_selects_specialized_workflows(query, expected_agent, expected_tool):
    service = AgentDispatchService()
    context = RequestContext.from_values(
        tenant_id="tenant-18",
        user_role="crew_chief",
        approval_scope=ApprovalScope.propose,
    )

    plan = service.dispatch(query, context=context)

    assert plan.agent_name == expected_agent
    assert expected_tool in plan.tool_calls[0].tool_name
    assert plan.tool_calls[0].audit.tenant_id == "tenant-18"
    assert plan.tool_calls[0].audit.request_scope is ApprovalScope.propose


def test_tool_approval_policy_blocks_critical_calls_without_approval():
    policy = SafetyPolicy()
    context = RequestContext.from_values(
        tenant_id="tenant-19",
        user_role="crew_chief",
        approval_scope=ApprovalScope.propose,
        request_id="req-19",
    )
    tool_call = TypedMCPToolCall.from_context(
        tool_name="setup.change",
        arguments={"front_wing": 2},
        context=context,
        audit_source="command_center",
        approval_required=True,
    )

    decision = policy.check_tool_call(tool_call, approval_granted=False)

    assert decision["blocked"] is True
    assert decision["approval_required"] is True
    assert decision["audit"]["tenant_id"] == "tenant-19"
    assert "approval" in decision["reason"].lower()


def test_tool_approval_policy_allows_read_only_calls():
    policy = SafetyPolicy()
    context = RequestContext.from_values(
        tenant_id="tenant-19",
        user_role="viewer",
        approval_scope=ApprovalScope.read_only,
    )
    tool_call = TypedMCPToolCall.from_context(
        tool_name="rag_cag.retrieve",
        arguments={"query": "latest stint"},
        context=context,
        audit_source="knowledge_service",
        approval_required=False,
    )

    decision = policy.check_tool_call(tool_call, approval_granted=False)

    assert decision["blocked"] is False
    assert decision["approval_required"] is False
    assert decision["tool_call"]["tool_name"] == "rag_cag.retrieve"
