# Tasks: Initial Implementation - 16 Race AI Copilot

## Phase 1: Foundation & Migration
- [x] 1.1 **Project Scaffold**: Create `backend/src/race_ai_copilot/` and `frontend/src/` directory structures.
    - **Files**: `backend/pyproject.toml`, `frontend/package.json`
    - **Verification**: Directory tree verification
- [x] 1.2 **FastAPI Shell**: Implement `main.py` with basic FastAPI app and `/health` endpoint.
    - **Files**: `backend/src/race_ai_copilot/main.py`
    - **Verification**: `curl http://localhost:8000/health`
- [ ] 1.3 **Infrastructure Setup**: Configure `docker-compose.yml` to orchestrate FastAPI, React, and Ollama.
    - **Files**: `docker-compose.yml`
    - **Verification**: `docker-compose up -d`
- [x] 1.4 **Asset Migration**: Move existing prompts and policies to the new structure.
    - **Files**: `backend/src/race_ai_copilot/prompts/`
    - **Verification**: File existence check
- [ ] 1.5 **Schema Definitions**: Define Pydantic models for `ChatRequest`, `ChatResponse`, `ToolCall`, `EvidencePacket`, and `Source`.
    - **Files**: `backend/src/race_ai_copilot/models/schemas.py`
    - **Verification**: Pytest model validation

## Phase 2: Backend Core (The Brain)
- [ ] 2.1 **Ollama Service**: Implement `OllamaService` for REST API communication with the local LLM.
    - **Files**: `backend/src/race_ai_copilot/services/ollama.py`
    - **Verification**: Pytest with mocked Ollama response
- [ ] 2.2 **Intent Classifier**: Implement `IntentClassifier` to categorize user requests (Telemetry, Setup, Parts, etc.).
    - **Files**: `backend/src/race_ai_copilot/core/reasoning.py`
    - **Verification**: Pytest (input "tire temps" -> output "Telemetry")
- [ ] 2.3 **Tool Planner**: Implement `ToolPlanner` to generate a sequence of tool calls based on intent.
    - **Files**: `backend/src/race_ai_copilot/core/reasoning.py`
    - **Verification**: Pytest (validate plan structure)
- [ ] 2.4 **Answer Composer**: Implement `AnswerComposer` to synthesize the final grounded response.
    - **Files**: `backend/src/race_ai_copilot/core/reasoning.py`
    - **Verification**: Pytest (verify output contains evidence)
- [ ] 2.5 **Reasoning Engine Orchestrator**: Wire `Classifier -> Planner -> Composer` into a cohesive `ReasoningEngine`.
    - **Files**: `backend/src/race_ai_copilot/core/reasoning.py`
    - **Verification**: Integration test (mock tools)

## Phase 3: Grounding & Tools
- [x] 3.1 **MCP Client**: Implement `MCPClient` to execute tools via the MCP Gateway.
    - **Files**: `backend/src/race_ai_copilot/clients/mcp_client.py`
    - **Verification**: `python -m py_compile`
- [x] 3.2 **Knowledge Service**: Implement RAG/CAG retrieval logic for technical documentation.
    - **Files**: `backend/src/race_ai_copilot/clients/rag_cag_client.py`
    - **Verification**: `python -m py_compile`
- [x] 3.3 **Evidence Builder**: Implement `EvidenceBuilder` to construct `EvidencePacket` from RAG and MCP results.
    - **Files**: `backend/src/race_ai_copilot/reasoning/evidence_planner.py`
    - **Verification**: `python -m py_compile`, validates `EvidencePacket` creation
- [ ] 3.4 **Grounding Integration**: Integrate `EvidenceGatherer` into the `ReasoningEngine` pipeline.
    - **Files**: `backend/src/race_ai_copilot/core/reasoning.py`
    - **Verification**: Integration test (end-to-end core flow)

## Phase 4: Governance & Guardrails
- [x] 4.1 **Approval Guard**: Implement `ApprovalGuard` to intercept and flag critical setup/strategy changes.
    - **Files**: `backend/src/race_ai_copilot/guardrails/approval_guard.py`
    - **Verification**: Pytest (critical action -> approval required)
- [x] 4.2 **Evidence Guard**: Implement `EvidenceRequiredGuard` to validate that the response is grounded in collected evidence.
    - **Files**: `backend/src/race_ai_copilot/guardrails/evidence_required_guard.py`
    - **Verification**: Pytest (ungrounded claim -> passed: false)
- [x] 4.3 **Race Decision Guard**: Implement `RaceDecisionGuard` to sanitize forbidden decision phrases.
    - **Files**: `backend/src/race_ai_copilot/guardrails/race_decision_guard.py`
    - **Verification**: Pytest (forbidden phrases replaced)
- [x] 4.4 **Safety Policy**: Implement `SafetyPolicy` that integrates all guards into a unified check.
    - **Files**: `backend/src/race_ai_copilot/guardrails/safety_policy.py`
    - **Verification**: Pytest (compiled safety report)
- [x] 4.5 **Config Update**: Add MCP_GATEWAY_URL, RAG_CAG_URL, and feature flags to settings.
    - **Files**: `backend/src/race_ai_copilot/config.py`
    - **Verification**: `python -m py_compile`
- [ ] 4.6 **Governance Pipeline**: Insert `ApprovalGuard` (after planning) and `EvidenceGuard` (before composing) into the engine.
    - **Files**: `backend/src/race_ai_copilot/core/reasoning.py`
    - **Verification**: Integration test (full guarded flow)

## Phase 5: Frontend Implementation
- [ ] 5.1 **State Management**: Setup Zustand store for chat history, tool traces, and evidence state.
    - **Files**: `frontend/src/store/useChatStore.ts`
    - **Verification**: Console log state updates
- [ ] 5.2 **Chat Shell**: Implement the main chat UI with streaming message support.
    - **Files**: `frontend/src/components/ChatShell.tsx`
    - **Verification**: Visual check (messages streaming)
- [ ] 5.3 **Tool Timeline**: Implement a visual trace of the reasoning process (Classifier -> Planner -> Tools).
    - **Files**: `frontend/src/components/ToolTimeline.tsx`
    - **Verification**: Visual check (timeline renders `tool_trace`)
- [ ] 5.4 **Evidence Drawer**: Implement a sidebar to display source citations and raw evidence snippets.
    - **Files**: `frontend/src/components/EvidenceDrawer.tsx`
    - **Verification**: Visual check (sources render from `EvidencePacket`)
- [ ] 5.5 **API Integration**: Connect frontend to `POST /api/chat` with Server-Sent Events (SSE) or WebSockets.
    - **Files**: `frontend/src/api/chat.ts`
    - **Verification**: End-to-end chat interaction
- [ ] 5.6 **Approval Modal**: Implement a UI modal to handle `pending_approval` states from the backend.
    - **Files**: `frontend/src/components/ApprovalModal.tsx`
    - **Verification**: Visual check (modal appears on critical action)

## Phase 6: Verification & Evals
- [ ] 6.1 **Core Unit Tests**: Write unit tests for `IntentClassifier` and `ToolPlanner`.
    - **Files**: `backend/tests/unit/test_reasoning.py`
    - **Verification**: `pytest`
- [ ] 6.2 **Service Integration Tests**: Verify connectivity with Ollama and MCP Gateway.
    - **Files**: `backend/tests/integration/test_services.py`
    - **Verification**: `pytest`
- [ ] 6.3 **E2E Chat Flow**: Implement Playwright tests for the full User Input $\to$ Response $\to$ Evidence loop.
    - **Files**: `tests/e2e/test_chat_flow.spec.ts`
    - **Verification**: `npx playwright test`
- [ ] 6.4 **Governance Validation**: Verify that critical actions are blocked until approved by the Crew Chief.
    - **Files**: `tests/e2e/test_governance.spec.ts`
    - **Verification**: `npx playwright test`
- [ ] 6.5 **Groundedness Eval**: Run a set of queries to verify that `EvidenceGuard` correctly flags hallucinations.
    - **Files**: `backend/tests/evals/test_groundedness.py`
    - **Verification**: Groundedness score > 0.8
