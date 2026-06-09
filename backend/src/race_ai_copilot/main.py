"""FastAPI application entry point for the Race AI Copilot."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


def _configure_otel(app: FastAPI, service_name: str = "race-ai-copilot") -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("OTEL setup failed (non-fatal): %s", exc)

from .clients.mcp_client import MCPClient
from .insforge_auth import InsForgeAuthMiddleware
from .rate_limit import RateLimitMiddleware
from .clients.rag_cag_client import RAGCAGClient
from .config import get_settings
from .guardrails.approval_guard import ApprovalGuard
from .guardrails.evidence_required_guard import EvidenceRequiredGuard
from .guardrails.race_decision_guard import RaceDecisionGuard
from .guardrails.safety_policy import SafetyPolicy
from .llm.ollama_client import OllamaClient, OllamaConfig
from .reasoning.composer import AnswerComposer, PromptBuilder
from .reasoning.evidence_planner import EvidenceBuilder
from .reasoning.intent_classifier import IntentClassifier
from .reasoning.tool_planner import ToolPlanner
from .conversation_store import init_conversation_db
from .routers import chat as chat_router
from .routers import health as health_router
from .services.chat_service import ChatService

# ------------------------------------------------------------------
# Lifespan — initialise / tear down resources
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle.

    On startup we create all client and service singletons and store
    them in ``app.state`` so they are available to route handlers via
    dependency injection overrides.
    """
    # ---- DB init ----
    await init_conversation_db()

    # ---- Read settings ----
    settings = get_settings()

    # ---- Clients ----
    ollama_client = OllamaClient(
        config=OllamaConfig(
            base_url=settings.ollama_url,
            model="race-copilot",
        )
    )
    rag_cag_client = RAGCAGClient(base_url=settings.rag_cag_url)
    mcp_client = MCPClient(gateway_url=settings.mcp_gateway_url)

    # ---- Reasoning components ----
    intent_classifier = IntentClassifier(llm_client=ollama_client)
    tool_planner = ToolPlanner(llm_client=ollama_client)
    evidence_builder = EvidenceBuilder()
    prompt_builder = PromptBuilder()
    answer_composer = AnswerComposer(llm_client=ollama_client)

    # ---- Guardrails ----
    approval_guard = ApprovalGuard()
    evidence_guard = EvidenceRequiredGuard()
    decision_guard = RaceDecisionGuard()
    safety_policy = SafetyPolicy(
        approval_guard=approval_guard,
        evidence_guard=evidence_guard,
        decision_guard=decision_guard,
    )

    # ---- Main service ----
    chat_service = ChatService(
        llm_client=ollama_client,
        rag_cag_client=rag_cag_client,
        mcp_client=mcp_client,
        intent_classifier=intent_classifier,
        tool_planner=tool_planner,
        evidence_builder=evidence_builder,
        prompt_builder=prompt_builder,
        answer_composer=answer_composer,
        approval_guard=approval_guard,
        evidence_guard=evidence_guard,
        decision_guard=decision_guard,
    )

    # ---- Store in app.state for dependency injection ----
    app.state.chat_service = chat_service
    app.state.safety_policy = safety_policy
    app.state.settings = settings

    # ---- Override the chat router's dependency ----
    async def _get_chat_service() -> ChatService:
        return chat_service

    app.dependency_overrides[chat_router.get_chat_service] = _get_chat_service

    yield

    # ---- Cleanup ----
    app.dependency_overrides.clear()


# ------------------------------------------------------------------
# Application factory
# ------------------------------------------------------------------

_REQUEST_COUNT = Counter(
    "copilot_http_requests_total", "Total HTTP requests", ["method", "path", "status_code"]
)
_REQUEST_LATENCY = Histogram(
    "copilot_http_request_duration_seconds", "HTTP request duration", ["method", "path"]
)

app = FastAPI(
    title="Race AI Copilot API",
    description="AI-powered copilot for race engineering — "
    "grounded in real telemetry, setup, and parts data.",
    version="0.1.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------
# Register routers
# ------------------------------------------------------------------

@app.middleware("http")
async def _metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    with _REQUEST_LATENCY.labels(method=method, path=path).time():
        response = await call_next(request)
    _REQUEST_COUNT.labels(method=method, path=path, status_code=response.status_code).inc()
    return response


@app.get("/metrics", include_in_schema=False)
async def _metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.add_middleware(InsForgeAuthMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")))
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)

# ── Global exception handlers ──────────────────────────────────────
import logging
_logger = logging.getLogger("race-ai-copilot")

@app.exception_handler(422)
async def _validation_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": str(exc.errors()) if hasattr(exc, "errors") else str(exc),
        },
    )

@app.exception_handler(404)
async def _not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "detail": "The requested resource was not found."},
    )

@app.exception_handler(Exception)
async def _generic_handler(request: Request, exc):
    _logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "An internal error occurred."},
    )

app.include_router(health_router.router)
app.include_router(chat_router.router, prefix="/api/v1")

_configure_otel(app)

# ------------------------------------------------------------------
# Static files (frontend SPA)
# ------------------------------------------------------------------

STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "static"

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all route to serve the SPA index.html for client-side routing."""
        if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("metrics"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        from fastapi import HTTPException
        raise HTTPException(status_code=404)


# ------------------------------------------------------------------
# Direct execution
# ------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.src.race_ai_copilot.main:app",
        host="0.0.0.0",
        port=8160,
        reload=True,
    )
