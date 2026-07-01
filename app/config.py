"""Centralized application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables and optional ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"

    # "openai" uses the live LLM when a key is set; "mock" forces fallback.
    ai_provider: str = "mock"
    openai_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    http_timeout_seconds: float = 15.0


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
