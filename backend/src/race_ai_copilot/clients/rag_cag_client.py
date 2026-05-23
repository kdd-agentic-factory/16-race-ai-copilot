import httpx
from typing import Dict, Any


class RAGCAGClient:
    """Client for retrieving grounding context from the RAG/CAG service."""

    def __init__(self, base_url: str = "http://localhost:8020", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Searches the RAG/CAG service for context relevant to the given query.

        Args:
            query: The search query string.
            top_k: Maximum number of context results to return.

        Returns:
            A dictionary containing the search results (sources, snippets, etc.).

        Raises:
            httpx.HTTPError: If the RAG/CAG service returns an error status.
            httpx.TimeoutException: If the request exceeds the configured timeout.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/search",
                json={"query": query, "top_k": top_k},
            )
            response.raise_for_status()
            return response.json()
