from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    mcp_gateway_url: str = Field(default="http://localhost:8010", alias="MCP_GATEWAY_URL")
    rag_cag_url: str = Field(default="http://localhost:8020", alias="RAG_CAG_URL")
    skills_url: str = Field(default="http://localhost:8030", alias="SKILLS_URL")
    orchestrator_url: str = Field(default="http://localhost:8000", alias="ORCHESTRATOR_URL")
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    postgres_url: str = Field(default="postgresql://kdd:kdd@localhost:5432/kdd", alias="POSTGRES_URL")
    default_model: str = Field(default="qwen2.5:7b", alias="COPILOT_DEFAULT_MODEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
