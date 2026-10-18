"""Application configuration loaded from environment."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """DeepDive settings — all secrets from env only."""

    mesh_api_key: str = Field(default="", alias="MESH_API_KEY")
    mesh_base_url: str = "https://api.meshapi.ai/v1"
    mesh_model: str = Field(default="openai/gpt-4o", alias="MESH_MODEL")

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    database_url: str = "sqlite:///deepdive.db"

    max_research_rounds: int = 3
    max_sources_per_round: int = 10
    max_claims: int = 100
    confidence_threshold: float = 0.7
    request_timeout: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
