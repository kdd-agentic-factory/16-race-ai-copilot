# Paper Integration

Paper-facing workflows should emit reproducibility notes, evidence references, assumptions, limitations, and links to KDD governance artifacts.

## Contribution

A local LLM-based race engineering copilot, deployed through Ollama and governed by MCP, RAG/CAG, Skills and KDD policies, enabling explainable interaction with telemetry, setup recommendations, circuit-specific part design and pattern discovery.

Spanish version:

Un copiloto conversacional local basado en LLM, desplegado mediante Ollama y gobernado por MCP, RAG/CAG, Skills y politicas KDD, que permite una interaccion explicable con la telemetria, las recomendaciones de setup, el diseno de piezas especificas por circuito y el descubrimiento de patrones.

## Command Center Integration

The `15-race-command-center` AI Copilot panel calls `16-race-ai-copilot` through `POST /integrations/race-command-center/chat`. The copilot does not fabricate telemetry or execute operational actions directly. It classifies the user request, proposes evidence retrieval, routes tool calls through governed platform services, and returns traceable answer metadata.

Runtime route:

`15-race-command-center panel -> 16-race-ai-copilot -> 03-rag-cag-knowledge-layer -> 02-mcp-gateway -> 01-agent-orchestrator -> 15-race-command-center APIs`

Representative research workflows:

- Tire degradation analysis from the latest stint.
- Base setup versus qualifying setup comparison.
- Explainable rear rebound setup recommendation.
- Pre-GP report generation for Jerez.
- Similar spin pattern discovery across previous sessions.
- Circuit-specific front brake cooling part proposal.

Critical setup or part-design recommendations are marked as requiring human approval and must include evidence references before operational use.
