# Proposal: Initial Implementation of 16-Race AI Copilot

## Intent
Establish a production-ready, evidence-grounded AI copilot for race engineering that replaces current prototype mocks with a robust service-oriented architecture.

## Scope

### In Scope
- **Structural Migration**: Move project to a clean `backend/` (FastAPI) and `frontend/` (React) split.
- **Reasoning Engine**: Implementation of the `Intent -> Plan -> Evidence -> Compose` cycle.
- **Guardrails**: Integration of Approval and Evidence verification layers.
- **Infrastructure Integration**: Connect with Ollama (LLM), MCP Gateway (Tools), and RAG/CAG (Context).
- **Chat UI**: React implementation featuring an Evidence Drawer and Tool Timeline.

### Out of Scope
- Integration with real-time telemetry streams (deferred to V4).
- Multi-user collaboration features.
- Full simulation engine implementation (deferred to V3).

## Capabilities

### New Capabilities
- `reasoning-engine`: Orchestrates the logic from user intent to final response via planning and evidence gathering.
- `guardrails`: Ensures response safety and correctness through approval steps and evidence grounding.
- `mcp-integration`: Manages communication with the MCP Gateway to execute race engineering tools.
- `rag-cag-system`: Implements retrieval augmented generation and cache augmented generation for technical race data.
- `chat-ui`: Provides the user interface for interaction, including specialized views for evidence and tool traces.
- `backend-api`: Provides the REST/WebSocket API for frontend-backend communication and orchestration.

### Modified Capabilities
- None

## Approach
Iterative migration and implementation:
1. **Foundation**: Migration of existing schemas, prompts, and policies to the new structure.
2. **MVP (Core Chat)**: Basic FastAPI backend + React UI + Ollama integration.
3. **V2 (Tooling/RAG)**: Integration of MCP Gateway and RAG/CAG systems.
4. **V3 (Simulations/Reports)**: Advanced reasoning for simulation analysis and automated report generation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/` | New | Complete FastAPI implementation of services and API. |
| `frontend/` | New | React application with state management and specialized UI components. |
| `openspec/` | New | Addition of specifications for all new capabilities. |
| `root/` | Modified | Removal of prototype/mock files and redirection to new structure. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Hallucinations | High | Strict Evidence-based grounding and Guardrail verification. |
| Latency | Medium | Implementation of CAG (Cache Augmented Generation) and streaming responses. |
| Security | Medium | Strict MCP tool permissions and input validation via Guardrails. |

## Rollback Plan
Since this is an initial implementation, rollback consists of reverting the git commit and returning to the prototype state. Project backups will be maintained during migration.

## Dependencies
- Ollama (local LLM runtime).
- MCP Gateway (deployed and accessible).
- Vector Database for RAG.

## Success Criteria
- [ ] Application runs with `backend/` and `frontend/` separation.
- [ ] Chat flow follows `Intent -> Plan -> Evidence -> Compose`.
- [ ] Guardrails successfully block ungrounded responses.
- [ ] UI displays Evidence Drawer and Tool Timeline correctly.
- [ ] Integration with Ollama and MCP is verified.
