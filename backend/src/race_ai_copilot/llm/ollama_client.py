import httpx
import json
from typing import List, Dict, Any, AsyncGenerator, Optional
from pydantic import BaseModel, Field

class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "race-copilot"
    timeout: float = 30.0

class OllamaClient:
    """Client for interacting with a local Ollama instance."""

    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()

    async def generate(
        self, 
        prompt: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generates a non-streamed response for a given prompt."""
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": options or {}
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")

    async def generate_stream(
        self, 
        prompt: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Generates a streamed response for a given prompt."""
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": True,
            "options": options or {}
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
                        if chunk.get("done"):
                            break

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handles a non-streamed chat interaction."""
        url = f"{self.config.base_url}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": options or {}
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")

    async def chat_stream(
        self, 
        messages: List[Dict[str, str]], 
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Handles a streamed chat interaction."""
        url = f"{self.config.base_url}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "options": options or {}
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk:
                            yield chunk["message"].get("content", "")
                        if chunk.get("done"):
                            break
