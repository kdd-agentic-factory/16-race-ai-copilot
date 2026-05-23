from typing import List, Dict, Any, Optional
from ..models.schemas import EvidencePacket, ToolCallRecord
from ..llm.ollama_client import OllamaClient

class PromptBuilder:
    """Assembles the final prompt for the LLM, including context and evidence."""

    def __init__(self, system_prompt: str = "You are the Race AI Copilot, a senior race engineer."):
        self.system_prompt = system_prompt

    def build_grounded_prompt(
        self, 
        query: str, 
        history: List[Dict[str, str]], 
        evidence: Optional[EvidencePacket] = None,
        tool_trace: Optional[List[ToolCallRecord]] = None
    ) -> str:
        """
        Constructs a prompt that forces the LLM to use the provided evidence.
        """
        prompt_parts = [self.system_prompt, "\n### Conversation History:"]
        for msg in history:
            prompt_parts.append(f"{msg['role']}: {msg['content']}")

        if evidence:
            prompt_parts.append("\n### Grounding Evidence:")
            for i, item in enumerate(evidence.sources):
                prompt_parts.append(f"[{i+1}] {item.title}: {item.snippet}")
            if evidence.raw_data:
                prompt_parts.append("\nAdditional Raw Data:")
                prompt_parts.extend(evidence.raw_data)

        if tool_trace:
            prompt_parts.append("\n### Tool Execution Trace:")
            for call in tool_trace:
                prompt_parts.append(f"Called {call.tool_name} with {call.parameters} -> Result: {call.result}")

        prompt_parts.append(f"\n### User Query: {query}")
        prompt_parts.append("\nInstructions: Use the provided evidence to answer. If evidence is missing or contradictory, state it clearly. Cite sources using [1], [2], etc.")

        return "\n".join(prompt_parts)

class AnswerComposer:
    """Synthesizes the final response from the LLM using the built prompt."""

    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client

    async def compose(
        self,
        prompt: str,
        stream: bool = False,
    ) -> Any:
        """Generate the final response — streamed or non-streamed.

        When *stream* is ``True`` the caller receives an async generator
        that yields tokens as they arrive from Ollama.
        """
        if stream:
            return self.llm_client.generate_stream(prompt)
        return await self.llm_client.generate(prompt)
