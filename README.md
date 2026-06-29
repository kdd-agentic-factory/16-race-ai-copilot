# 16 Race AI Copilot

Race AI Copilot is the conversational intelligence layer for the KDD agentic race engineering platform. It helps crew chiefs, data engineers, analysts, and developers ask grounded questions about telemetry, setup changes, race sessions, documentation, skills, and pre-Grand Prix preparation.

This repository is designed as an operational copilot, not a plain chat box. Every answer should separate observed telemetry, inferred patterns, model predictions, recommendations, evidence, and approval state.

## MVP Stack

- Local LLM: Ollama
- Chat UI: OpenWebUI
- API backend: FastAPI
- Tool calling: MCP Gateway
- Knowledge: RAG/CAG Knowledge Layer
- Skills: Skills Registry
- Orchestration: Agent Orchestrator
- Memory and evidence stores: PostgreSQL and Qdrant

## Core Use Cases

- Compare FP1 and FP2 telemetry in a specific corner.
- Explain tire degradation after a given lap.
- Recommend setup changes for stop-and-go tracks and high track temperature.
- Propose aero or cooling parts to test.
- Summarize anomalies from the latest session.
- Generate a crew chief report.
- Draft ADRs for platform architecture changes.
- Search for similar patterns in historical sessions.
- Compare engine maps at corner exit.
- Explain evidence behind setup recommendations.

## API

The canonical MVP API is implemented in `backend/src/race_ai_copilot` and exposes:

- `GET /health`
- `POST /chat`
- `POST /chat/stream`
- `POST /integrations/race-command-center/chat`
- `POST /tools/call`
- `POST /recommendations/setup`
- `POST /analysis/telemetry`
- `POST /analysis/patterns`
- `POST /reports/crew-chief`

`15-race-command-center` should use the dedicated integration endpoint for its `AI Copilot` panel. The endpoint accepts Command Center context such as session, stint, circuit, base setup, proposed setup, and vehicle metadata, then returns an evidence-gated `CopilotResponse` with proposed calls through RAG/CAG, MCP Gateway, Agent Orchestrator, and Command Center APIs.

`services/copilot-api/app` remains as a frozen compatibility shim for older launch commands.

## Run Locally

```bash
docker compose -f docker-compose.copilot.yml up --build
```

Services:

- API: `http://localhost:8160`
- OpenWebUI: `http://localhost:8088`
- Ollama: `http://localhost:11434`

## Development

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn race_ai_copilot.main:app --host 0.0.0.0 --port 8160 --reload
```

## Safety Principles

The copilot must never invent telemetry evidence. High-risk setup, strategy, deployment, Kubernetes, and GitHub actions require human approval and should be requested through the orchestrator rather than executed directly.

## Tradeoffs

### Token handling: local JWT validation vs. auth API verification

**What**: JWT tokens are validated locally using HS256 with a shared secret (`JWT_SECRET` env var). No HTTP call to InsForge Auth API on every request.

**Why**: Reduces latency (no extra HTTP round-trip per request) and works offline. The shared secret is set during deployment and rotates with the service.

**Risk**: If a token is revoked server-side, the copilot won't detect it until the token expires. This is acceptable for a racing environment where sessions are short-lived (typically < 2 hours).

**Mitigation**: Token expiry is enforced. For critical operations (e.g., proposing setup changes to the crew chief), the copilot can call the auth API explicitly to verify token validity.

**Alternative considered**: Verify against InsForge Auth API on every request — rejected due to latency impact in real-time racing context where sub-second responses matter.
