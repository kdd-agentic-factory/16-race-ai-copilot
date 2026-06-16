from __future__ import annotations

from race_ai_copilot.models.schemas import ChatResponse, EvidenceItem
from race_ai_copilot.models.ui import OpenWebUIChatRequest, OpenWebUIMessage
from race_ai_copilot.reasoning.evidence_planner import EvidenceBuilder
from race_ai_copilot.reasoning.tool_planner import ToolPlanner
from race_ai_copilot.services.ui_adapter_service import UIAdapterService
from race_ai_copilot.contracts import RequestContext, TenantMetadata


class _StaticLLM:
    def __init__(self, response_text: str | None = None, should_raise: bool = False):
        self.response_text = response_text
        self.should_raise = should_raise

    async def generate(self, prompt: str) -> str:
        if self.should_raise:
            raise RuntimeError("boom")
        return self.response_text or "[]"


def test_tool_planner_parses_llm_json_and_falls_back_on_error():
    parsed_plan = __import__("asyncio").run(
        ToolPlanner(_StaticLLM('noise before [ {"tool_name": "get_telemetry_data", "parameters": {"sensor": "tire_temp"}} ] after')).plan(
            "Telemetry", "inspect tire temp"
        )
    )
    fallback_plan = __import__("asyncio").run(
        ToolPlanner(_StaticLLM(should_raise=True)).plan("Setup", "change balance")
    )
    empty_plan = __import__("asyncio").run(ToolPlanner(_StaticLLM("[]")).plan("General", "hello"))

    assert parsed_plan[0].tool_name == "get_telemetry_data"
    assert parsed_plan[0].parameters == {"sensor": "tire_temp"}
    assert [item.tool_name for item in fallback_plan] == ["get_current_setup", "suggest_setup_change"]
    assert empty_plan == []


def test_evidence_builder_handles_accumulated_and_raw_inputs():
    packet = EvidenceBuilder().build(
        rag_results={"sources": [{"id": "doc-1", "title": "Telemetry Notes", "path": "/tmp/notes.md", "text": "alpha"}, "orphan-source"]},
        mcp_results={
            "telemetry.compare": {"data": {"lap_delta": "0.128", "corner": None}},
            "patterns.search": {"result": {"similar_sessions": 3}},
        },
    )

    assert packet.sources[0].id == "doc-1"
    assert packet.raw_data[0] == "orphan-source"
    assert "lap_delta: 0.128" in packet.raw_data
    assert "similar_sessions: 3" in packet.raw_data
    assert packet.groundedness_score > 0


def test_ui_adapter_uses_latest_user_message_and_falls_back_without_one():
    adapter = UIAdapterService()
    context = RequestContext.from_values(tenant_id="tenant-7", user_role="viewer")

    request = OpenWebUIChatRequest(
        messages=[
            OpenWebUIMessage(role="system", content="ignore"),
            OpenWebUIMessage(role="assistant", content="also ignore"),
            OpenWebUIMessage(role="user", content="latest user message"),
        ],
        context={"lane": "A"},
    )
    canonical = adapter.to_canonical_request(request, context)

    fallback_request = OpenWebUIChatRequest(messages=[OpenWebUIMessage(role="assistant", content="assistant fallback")])
    fallback_canonical = adapter.to_canonical_request(fallback_request, context)

    assert canonical.message == "latest user message"
    assert canonical.context["tenant_id"] == "tenant-7"
    assert fallback_canonical.message == "assistant fallback"


def test_ui_adapter_stream_events_keep_blank_answers_and_done_marker():
    adapter = UIAdapterService()
    events = adapter.stream_events(ChatResponse(conversation_id="conv-1", message_id="msg-1", answer="", evidence=[EvidenceItem(id="e1", title="t", url_or_path="u", snippet="s")]))

    assert events[-1] == "event: done\ndata: [DONE]\n\n"
    assert events[0] == "data: \n\n"
