# Agent Operating Guide

This repository implements the Race AI Copilot for the KDD agentic factory.

## Expected Agent Behavior

- Ground answers in RAG/CAG, telemetry evidence, previous sessions, or explicit model output.
- Clearly label observed telemetry, inferred patterns, predictions, recommendations, and unknowns.
- Use MCP Gateway, Skills Registry, and Agent Orchestrator through client integrations.
- Do not directly execute Kubernetes, GitHub, setup, or deployment actions.
- Mark critical setup recommendations as requiring human approval.
- Preserve traceability by returning evidence and tool-call metadata.

## Local Boundaries

- API code lives in `backend/src/race_ai_copilot`; `services/copilot-api/app` is a frozen compatibility shim.
- Cross-platform clients live in `integrations`.
- Prompt and policy assets are versioned under `prompts` and `policies`.
- Schemas are versioned under `data-contracts`.
