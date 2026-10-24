"""Application configuration loaded from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """DeepDive settings — all secrets from env only."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    mesh_api_key: str = Field(default="", alias="MESH_API_KEY")
    mesh_base_url: str = "https://api.meshapi.ai/v1"
    mesh_model: str = Field(default="anthropic/claude-haiku-5.5", alias="MESH_MODEL")
    mesh_max_output_tokens: int = Field(default=4096, ge=256, le=16384, alias="MESH_MAX_OUTPUT_TOKENS")
    mesh_json_attempts: int = Field(default=2, ge=1, le=3, alias="MESH_JSON_ATTEMPTS")
    brave_search_api_key: str = Field(default="", alias="BRAVE_SEARCH_API_KEY")

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    database_url: str = "sqlite:///deepdive.db"
    database_path: str = Field(default="deepdive.db", alias="DEEPDIVE_DB_PATH")

    max_research_rounds: int = 3
    max_sources_per_round: int = 10
    max_search_queries_per_round: int = 2
    max_claims: int = 12
    max_contradiction_batches: int = Field(default=3, ge=1, le=6, alias="MAX_CONTRADICTION_BATCHES")
    confidence_threshold: float = 0.7
    min_source_trust: float = Field(default=0.4, ge=0.0, le=1.0, alias="MIN_SOURCE_TRUST")
    request_timeout: int = 30

settings = Settings()
