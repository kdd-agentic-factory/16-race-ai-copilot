import httpx
from typing import Dict, Any


class MCPClient:
    """Client for executing tools via the MCP Gateway."""

    def __init__(self, gateway_url: str = "http://localhost:8010", timeout: float = 60.0):
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = timeout

    async def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Calls a tool on the MCP Gateway and returns the result as a dict.

        Args:
            tool_name: Name of the tool to execute.
            payload: Parameters to pass to the tool.

        Returns:
            The tool execution result as a dictionary.

        Raises:
            httpx.HTTPError: If the MCP Gateway returns an error status.
            httpx.TimeoutException: If the request exceeds the configured timeout.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.gateway_url}/tools/{tool_name}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
