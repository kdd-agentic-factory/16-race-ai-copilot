from __future__ import annotations

from race_ai_copilot.clients.mcp_client import MCPClient
from race_ai_copilot.contracts import ApprovalScope, RequestContext, TenantMetadata, TypedMCPToolCall


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_checked = False

    def raise_for_status(self):
        self.status_checked = True

    def json(self):
        return self._payload


class _FakeAsyncClient:
    last_instance = None

    def __init__(self, timeout):
        self.timeout = timeout
        self.requests = []
        _FakeAsyncClient.last_instance = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        self.requests.append((url, json))
        return _FakeResponse({"url": url, "json": json})


def test_call_tool_uses_gateway_tools_path_and_strips_trailing_slash(monkeypatch):
    monkeypatch.setattr("race_ai_copilot.clients.mcp_client.httpx.AsyncClient", _FakeAsyncClient)

    client = MCPClient(gateway_url="http://gateway.local/", timeout=12.5)
    result = __import__("asyncio").run(client.call_tool("session.create", {"foo": "bar"}))

    fake_client = _FakeAsyncClient.last_instance
    assert fake_client is not None
    assert fake_client.timeout == 12.5
    assert fake_client.requests == [("http://gateway.local/tools/session.create", {"foo": "bar"})]
    assert result["url"] == "http://gateway.local/tools/session.create"
    assert result["json"] == {"foo": "bar"}


def test_call_typed_tool_includes_audit_metadata(monkeypatch):
    monkeypatch.setattr("race_ai_copilot.clients.mcp_client.httpx.AsyncClient", _FakeAsyncClient)

    context = RequestContext.from_values(
        tenant_id="tenant-42",
        user_role="crew_chief",
        approval_scope=ApprovalScope.execute,
        request_id="req-123",
        session_id="sess-123",
        correlation_id="corr-123",
    )
    tool_call = TypedMCPToolCall.from_context(
        tool_name="telemetry.compare",
        arguments={"session_a": "FP1", "session_b": "FP2"},
        context=context,
        approval_required=True,
    )

    client = MCPClient(gateway_url="http://gateway.local")
    result = __import__("asyncio").run(client.call_typed_tool(tool_call))

    sent_payload = _FakeAsyncClient.last_instance.requests[0][1]
    assert sent_payload["tenant_id"] == "tenant-42"
    assert sent_payload["user_role"] == "crew_chief"
    assert sent_payload["approval_scope"] == "execute"
    assert sent_payload["request_id"] == "req-123"
    assert sent_payload["session_id"] == "sess-123"
    assert sent_payload["correlation_id"] == "corr-123"
    assert sent_payload["approved"] is False
    assert sent_payload["critical"] is True
    assert result["json"]["arguments"] == {"session_a": "FP1", "session_b": "FP2"}
