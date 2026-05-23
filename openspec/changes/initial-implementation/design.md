# Design: Initial Implementation - 16 Race AI Copilot

## Technical Approach

The system will be migrated from a mock-based prototype to a service-oriented architecture split into a FastAPI backend and a React frontend. The core logic is centered around a **Reasoning Engine** that implements a strict `Intent -> Plan -> Evidence -> Compose` cycle, ensuring all AI responses are grounded in actual race data. A **Governance Layer (Crew Chief)** will intercept critical actions for human approval, and **Guardrails** will validate response groundedness.

## Architecture Decisions

### Decision: Reasoning Engine Workflow
**Choice**: Sequential Pipeline (Classifier $\to$ Planner $\to$ Evidence Gatherer $\to$ Composer).
**Alternatives considered**: Single-prompt Agentic loop.
**Rationale**: In race engineering, predictability and traceability are paramount. A sequential pipeline allows for explicit guardrail insertion at each stage (e.g., ApprovalGuard after Planning) and provides a clear tool timeline for the user.

### Decision: State Management
**Choice**: Zustand for frontend state.
**Alternatives considered**: Redux, React Context.
**Rationale**: Zustand provides a lightweight, boilerplate-free way to manage the chat history, tool traces, and evidence packets across the `ChatShell` and `EvidenceDrawer` without the complexity of Redux.

### Decision: LLM Integration
**Choice**: Ollama via REST API.
**Alternatives considered**: Local transformers, Cloud LLMs.
**Rationale**: Adheres to the "Local-first Execution" requirement (NFR-1), ensuring data privacy and low latency during race weekends.

### Decision: Grounding Mechanism
**Choice**: Hybrid RAG/CAG (Retrieval Augmented / Cache Augmented Generation).
**Alternatives considered**: Fine-tuning.
**Rationale**: Race data (telemetry, circuit specs) changes rapidly. RAG allows real-time updates, while CAG ensures frequently accessed technical manuals are retrieved with minimal latency.

## Data Flow

```
User Input ──→ [FastAPI API] ──→ [Reasoning Engine]
                                      │
                                      ▼
                          1. Classifier (Intent) ──→ [Ollama]
                                      │
                                      ▼
                          2. Planner (Tool Plan) ──→ [Ollama]
                                      │
                                      ▼
                          3. Approval Guard ───→ (If Critical) ──→ [Pending Approval State]
                                      │                                  │
                                      ▼                                  └─→ [User Approval]
                          4. Evidence Gatherer ──→ [MCP Tools / RAG / CAG]
                                      │
                                      ▼
                          5. Composer (Response) ──→ [Ollama]
                                      │
                                      ▼
                          6. Evidence Guard ───→ [Validate Grounding]
                                      │
                                      ▼
[React Frontend] ←── [Streaming Response + Evidence Packet + Tool Trace]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/race_ai_copilot/main.py` | Create | FastAPI entry point and API routing. |
| `backend/src/race_ai_copilot/core/reasoning.py` | Create | Implementation of `ReasoningEngine` (Classifier, Planner, Composer). |
| `backend/src/race_ai_copilot/core/guardrails.py` | Create | `ApprovalGuard` and `EvidenceGuard` logic. |
| `backend/src/race_ai_copilot/services/ollama.py` | Create | Client for Ollama API interactions. |
| `backend/src/race_ai_copilot/services/mcp.py` | Create | Client for MCP Gateway tool execution. |
| `backend/src/race_ai_copilot/services/knowledge.py` | Create | RAG/CAG retrieval logic. |
| `backend/src/race_ai_copilot/models/schemas.py` | Create | Pydantic models for `ChatRequest`, `ChatResponse`, etc. |
| `frontend/src/components/ChatShell.tsx` | Create | Main layout for the AI Copilot. |
| `frontend/src/components/EvidenceDrawer.tsx` | Create | Sidebar for displaying evidence sources. |
| `frontend/src/components/ToolTimeline.tsx` | Create | Visual trace of the reasoning process. |
| `frontend/src/store/useChatStore.ts` | Create | Zustand store for conversation and engine state. |
| `docker-compose.yml` | Modify | Configure services for FastAPI, React, and Ollama. |

## Interfaces / Contracts

### Backend API
`POST /api/chat`
- **Request**: `ChatRequest { session_id: string, message: string }`
- **Response**: Streamed `ChatResponse`
  ```typescript
  interface ChatResponse {
    text: string; // Streamed tokens
    status: 'processing' | 'pending_approval' | 'complete';
    tool_trace: ToolCall[];
    evidence: EvidencePacket;
  }
  ```

### Internal Models
```python
class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Any]
    timestamp: datetime

class EvidencePacket(BaseModel):
    sources: List[Source]
    raw_data: List[str]

class Source(BaseModel):
    id: str
    title: str
    url_or_path: str
    snippet: str
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Classifier/Planner logic | Pytest with mocked Ollama responses. |
| Integration | MCP/RAG connectivity | Integration tests against local Ollama and Mock MCP Gateway. |
| E2E | Full Chat Flow | Playwright tests from User Input $\to$ Response $\to$ Evidence check. |
| Governance | Approval Interception | Test that critical tool calls trigger `pending_approval` status. |

## Migration / Rollout

1. **Phase 1 (Foundation)**: Setup `backend/` and `frontend/` directories. Move existing prompts and policies to `backend/src/race_ai_copilot/prompts/`.
2. **Phase 2 (Core)**: Implement `OllamaService` and basic chat endpoint.
3. **Phase 3 (Agentic)**: Implement `ReasoningEngine` and `MCPClient`.
4. **Phase 4 (Governance)**: Implement `ApprovalGuard` and the `ApprovalModal` in the frontend.

## Open Questions

- [ ] Which Vector DB will be used for the RAG system (ChromaDB vs Qdrant)?
- [ ] Definition of "critical" actions for the `ApprovalGuard` (need a comprehensive list of dangerous tools).
