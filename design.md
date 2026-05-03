# Race AI Copilot Design

## Purpose

`16-race-ai-copilot` is the conversational and agentic interface for the KDD race engineering platform. It turns user questions into grounded answers, tool calls, workflow requests, reports, and recommendations.

## Architecture

The copilot API receives chat and task requests, classifies intent, selects a model profile, gathers evidence from RAG/CAG and race data integrations, proposes tool calls, and returns a structured response.

```text
Chat UI / OpenWebUI
        |
        v
Copilot API
        |
        +-- Prompt Router
        +-- Safety Guard
        +-- Memory Service
        +-- Tool Calling Service
        |
        +-- Ollama Gateway
        +-- MCP Gateway
        +-- RAG/CAG Knowledge Layer
        +-- Skills Registry
        +-- Race Command Center
        +-- Agent Orchestrator
```

## Response Contract

Every operational answer should include:

1. Direct answer.
2. Evidence.
3. Interpretation.
4. Recommended action.
5. Approval status.
6. Next step.

## Approval Model

Low-risk analysis can be answered directly. Medium-risk recommendations are proposed with evidence. High-risk setup, deployment, or operational actions are blocked until a human approval workflow is created through the orchestrator.
