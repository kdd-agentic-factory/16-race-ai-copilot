from typing import List, Dict, Any
from ..models.schemas import ToolCallRecord

class ToolPlanner:
    """Maps classified intents to a sequence of MCP tool calls."""

    # Mapping intents to base tool names. 
    # In a production system, the parameters would be extracted from the query via LLM.
    INTENT_TOOL_MAPPING = {
        "Telemetry": ["get_telemetry_data", "analyze_sensor_trends"],
        "Setup": ["get_current_setup", "suggest_setup_change"],
        "Parts": ["search_parts_catalog", "get_part_specs"],
        "Simulation": ["run_simulation", "get_sim_results"],
        "General": []
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def plan(self, intent: str, query: str) -> List[ToolCallRecord]:
        """
        Generates a tool execution plan.
        For now, it uses the mapping and an LLM call to refine parameters.
        """
        base_tools = self.INTENT_TOOL_MAPPING.get(intent, [])
        if not base_tools:
            return []

        # Use LLM to determine the exact tool calls and parameters based on the query
        prompt = (
            f"Based on the intent '{intent}' and the user query '{query}', "
            f"generate a sequence of tool calls from this list: {base_tools}.\n\n"
            f"Return the result as a JSON list of objects with 'tool_name' and 'parameters' (a dict).\n"
            f"Example: [{{'tool_name': 'get_telemetry_data', 'parameters': {{'sensor': 'tire_temp'}}}}] "
            f"Return ONLY the JSON list."
        )

        try:
            response_text = await self.llm_client.generate(prompt)
            # Simple JSON extraction from LLM response
            import json
            # Find the first [ and last ] to handle potential LLM chatter
            start = response_text.find("[")
            end = response_text.rfind("]") + 1
            if start != -1 and end != 0:
                plan_data = json.loads(response_text[start:end])
                return [
                    ToolCallRecord(
                        tool_name=item["tool_name"], 
                        parameters=item.get("parameters", {})
                    ) for item in plan_data
                ]
        except Exception as e:
            # Fallback: provide the base tool with empty params if LLM fails
            return [ToolCallRecord(tool_name=tool, parameters={}) for tool in base_tools]

        return []
