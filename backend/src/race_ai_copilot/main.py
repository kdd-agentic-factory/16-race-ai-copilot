"""FastAPI application entry point for the Race AI Copilot.

Initialises all clients, services, guardrails, and registers the API
routers so the service is ready to accept requests.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from .clients.mcp_client import MCPClient
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

app.include_router(health_router.router)
app.include_router(chat_router.router, prefix="/api")


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
