from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables with defaults.

    Every field can be overridden via its alias (uppercase env var name).
    """

    # --- LLM ---
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")

    # --- MCP & RAG/CAG ---
    mcp_gateway_url: str = Field(
        default="http://localhost:8010", alias="MCP_GATEWAY_URL"
    )
    rag_cag_url: str = Field(
        default="http://localhost:8020", alias="RAG_CAG_URL"
    )

    # --- Feature flags ---
    enable_mock_mode: bool = Field(default=False, alias="ENABLE_MOCK_MODE")
    enable_approval_guard: bool = Field(
        default=True, alias="ENABLE_APPROVAL_GUARD"
    )
    enable_evidence_guard: bool = Field(
        default=True, alias="ENABLE_EVIDENCE_GUARD"
    )

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
