"""Configuration settings for g-copilot-proxy."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server settings
    app_name: str = "g-copilot-proxy"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # pi-ai bridge settings
    piai_module_path: str = "../ai"  # Path to @mariozechner/pi-ai
    piai_node_path: str = "node"  # Path to Node.js executable

    # GitHub Copilot settings
    copilot_base_url: str = "https://api.individual.githubcopilot.com"
    copilot_enterprise_url: Optional[str] = None

    # Authentication settings
    auth_mode: str = "passthrough"  # "passthrough" or "managed"
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer "

    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
