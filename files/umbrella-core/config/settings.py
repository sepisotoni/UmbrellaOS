"""
config/settings.py — Central configuration loaded from .env
All settings live here. Never import os.environ directly elsewhere.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://umbrella:changeme@localhost:5432/umbrella_core"
    database_url_sync: str = "postgresql+psycopg2://umbrella:changeme@localhost:5432/umbrella_core"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"

    # Initial admin bootstrap
    initial_admin_discord_id: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8765
    debug: bool = False

    # Optional — will be moved to DB settings after first boot
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_bot_token: str = ""
    rcon_host: str = "localhost"
    rcon_port: int = 25575
    rcon_password: str = ""
    openrouter_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance. Use this everywhere."""
    return Settings()
