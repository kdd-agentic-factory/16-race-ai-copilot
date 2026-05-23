from typing import Dict, List, Optional
from ..llm.ollama_client import OllamaClient

class IntentClassifier:
    """Categorizes user queries into predefined intents to drive tool planning."""

    INTENT_MAP = {
        "Telemetry": ["temp", "pressure", "sensor", "telemetry", "data", "wear", "degradation", "lap time"],
        "Setup": ["wing", "spring", "damping", "camber", "toe", "setup", "adjustment", "understeer", "oversteer"],
        "Parts": ["part", "component", "brake duct", "wing profile", "material", "specification", "compatibility"],
        "Simulation": ["sim", "simulate", "prediction", "forecast", "virtual run", "predict"],
        "General": []
    }

    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client

    def _classify_by_keywords(self, text: str) -> Optional[str]:
        """Fast keyword-based classification."""
        text_lower = text.lower()
        for intent, keywords in self.INTENT_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return intent
        return None

    async def classify(self, text: str) -> str:
        """
        Classifies the user intent. 
        Tries keywords first, then falls back to LLM for complex queries.
        """
        # 1. Try fast keyword mapping
        keyword_intent = self._classify_by_keywords(text)
        if keyword_intent:
            return keyword_intent

        # 2. Fallback to LLM for nuanced understanding
        prompt = (
            f"Analyze the following user query and classify it into exactly one of these intents: "
            f"Telemetry, Setup, Parts, Simulation, General.\n\n"
            f"Query: '{text}'\n\n"
            f"Return only the intent name."
        )
        
        try:
            result = await self.llm_client.generate(prompt)
            # Clean the LLM output and validate it's one of our intents
            cleaned_result = result.strip().replace(".", "")
            if cleaned_result in self.INTENT_MAP:
                return cleaned_result
        except Exception:
            # Fallback to General on error
            pass

        return "General"
