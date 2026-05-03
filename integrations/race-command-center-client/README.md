# Race Command Center Client

Client adapter for `15-race-command-center`. Used to fetch telemetry, sessions, anomalies, maps, and reports.

## AI Copilot Panel Contract

The `AI Copilot` panel in `15-race-command-center` should call:

`POST /integrations/race-command-center/chat`

The request is defined in `data-contracts/race-command-center-chat.schema.yaml`. The response uses `data-contracts/copilot-response.schema.yaml`.

Example request:

```json
{
  "query": "Analiza la degradacion del neumatico trasero en la ultima tanda.",
  "user_role": "crew_chief",
  "active_session_id": "jerez-fp2-2026-05-03",
  "circuit": "Jerez",
  "stint_id": "stint-3",
  "base_setup_id": "setup-base-jerez",
  "proposed_setup_id": "setup-q-jerez",
  "vehicle_context": {
    "car_id": "race-car-01",
    "tire_compound": "soft"
  }
}
```

The copilot returns a structured answer plus proposed tool calls. The intended route is:

`15-race-command-center panel -> 16-race-ai-copilot -> 03-rag-cag-knowledge-layer -> 02-mcp-gateway -> 01-agent-orchestrator -> 15-race-command-center APIs`

The API does not directly execute Command Center actions. It proposes calls with evidence requirements and approval metadata so the Command Center can display traceability before a human approves critical setup or design changes.

## Supported Panel Questions

- Analiza la degradacion del neumatico trasero en la ultima tanda.
- Compara el setup base con el setup propuesto para clasificacion.
- Explicame por que recomiendas cambiar el rebote trasero.
- Genera un informe pre-GP para el circuito de Jerez.
- Busca patrones de spin similares en sesiones anteriores.
- Que pieza especifica podriamos disenar para mejorar la refrigeracion del freno delantero.
