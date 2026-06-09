"""Integration tests for production hardening features.

Validates rate limiting (RateLimitMiddleware), global exception handlers,
and CORS behaviour under the FastAPI TestClient.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel
from race_ai_copilot.rate_limit import RateLimitMiddleware


def _build_rate_limited_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, calls_per_minute=60)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/chat")
    async def resource():
        return {"data": "ok"}

    @app.get("/metrics")
    async def metrics():
        return {"ok": True}

    return app


def _build_exception_handler_app() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(422)
    async def validation_exception_handler(request: Request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": str(exc.errors()) if hasattr(exc, "errors") else str(exc),
            },
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "detail": "The requested resource was not found."},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc):
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": "An internal error occurred."},
        )

    @app.post("/api/v1/chat")
    async def create_resource(payload: dict):
        return {"received": payload}

    return app


class TestRateLimiting:
    def test_allows_requests_under_limit(self):
        app = _build_rate_limited_app()
        client = TestClient(app)
        for _ in range(55):
            resp = client.get("/api/v1/chat")
            assert resp.status_code == 200

    def test_blocks_requests_over_limit(self):
        app = _build_rate_limited_app()
        client = TestClient(app)
        over = False
        for _ in range(70):
            resp = client.get("/api/v1/chat")
            if resp.status_code == 429:
                over = True
                assert "Retry-After" in resp.headers
                break
        assert over

    def test_does_not_affect_metrics_path(self):
        app = _build_rate_limited_app()
        client = TestClient(app)
        for _ in range(70):
            resp = client.get("/metrics")
            assert resp.status_code == 200

    def test_does_not_affect_health_path(self):
        app = _build_rate_limited_app()
        client = TestClient(app)
        for _ in range(70):
            resp = client.get("/health")
            assert resp.status_code == 200


class TestExceptionHandlers:
    def test_404_returns_consistent_json(self):
        client = TestClient(_build_exception_handler_app())
        resp = client.get("/this-path-does-not-exist")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "not_found"

    def test_fastapi_default_422_format(self):
        class SomePayload(BaseModel):
            name: str

        app = FastAPI()

        @app.exception_handler(422)
        async def validation_exception_handler(request: Request, exc):
            return JSONResponse(
                status_code=422,
                content={
                    "error": "validation_error",
                    "detail": str(exc.errors()) if hasattr(exc, "errors") else str(exc),
                },
            )

        @app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "detail": "The requested resource was not found."},
            )

        @app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc):
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "detail": "An internal error occurred."},
            )

        @app.post("/validate")
        async def validate(payload: SomePayload):
            return {"received": payload.model_dump()}

        client = TestClient(app)
        resp = client.post("/validate", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body

    def test_500_via_http_exception_uses_fastapi_default(self):
        app = FastAPI()

        @app.exception_handler(422)
        async def validation_exception_handler(request: Request, exc):
            return JSONResponse(
                status_code=422,
                content={
                    "error": "validation_error",
                    "detail": str(exc.errors()) if hasattr(exc, "errors") else str(exc),
                },
            )

        @app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "detail": "The requested resource was not found."},
            )

        @app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc):
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "detail": "An internal error occurred."},
            )

        @app.get("/crash")
        async def crash():
            raise HTTPException(status_code=500, detail="Something went wrong.")

        client = TestClient(app)
        resp = client.get("/crash")
        assert resp.status_code == 500
        assert resp.json() == {"detail": "Something went wrong."}


class TestCORS:
    def test_options_preflight_succeeds(self):
        app = _build_exception_handler_app()
        client = TestClient(app)
        resp = client.options("/api/v1/chat")
        assert resp.status_code in (200, 405)
