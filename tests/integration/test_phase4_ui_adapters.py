from __future__ import annotations

from race_ai_copilot.main import app


def test_openwebui_adapter_returns_openwebui_chat_shape():
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/integrations/openwebui/chat",
            headers={"X-Tenant-ID": "tenant-ui", "X-Request-ID": "req-ui-1"},
            json={
                "model": "race-copilot",
                "messages": [
                    {"role": "system", "content": "You are a race copilot."},
                    {"role": "user", "content": "Summarize the latest stint deltas."},
                ],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["object"] == "chat.completion"
        assert body["tenant_id"] == "tenant-ui"
        assert body["choices"][0]["message"]["role"] == "assistant"


def test_chat_poll_returns_canonical_response_for_polling_clients():
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/poll",
            headers={"X-Tenant-ID": "tenant-ui", "X-Request-ID": "req-ui-2"},
            json={"message": "Summarize the latest stint deltas for Jerez."},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["conversation_id"]
        assert body["answer"]
        assert body["approval_required"] in {True, False}


def test_chat_stream_emits_sse_events():
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/chat/stream",
            headers={"X-Tenant-ID": "tenant-ui", "X-Request-ID": "req-ui-3"},
            json={"message": "Summarize the latest stint deltas for Jerez."},
        ) as response:
            content = b"".join(response.iter_bytes()).decode("utf-8")

        assert response.status_code == 200
        assert "data:" in content
        assert "[DONE]" in content
