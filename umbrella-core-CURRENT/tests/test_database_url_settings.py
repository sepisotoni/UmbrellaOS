import pytest
from pydantic import ValidationError

from config.settings import Settings


def test_database_password_is_url_encoded_into_connection_templates(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:{DATABASE_PASSWORD}@db.example:5432/postgres",
    )
    monkeypatch.setenv(
        "DATABASE_URL_SYNC",
        "postgresql+psycopg2://postgres:{DATABASE_PASSWORD}@db.example:5432/postgres",
    )
    monkeypatch.setenv("DATABASE_PASSWORD", "p@ss/$#word")

    settings = Settings(_env_file=None)

    assert settings.database_url == (
        "postgresql+asyncpg://postgres:p%40ss%2F%24%23word"
        "@db.example:5432/postgres"
    )
    assert settings.database_url_sync == (
        "postgresql+psycopg2://postgres:p%40ss%2F%24%23word"
        "@db.example:5432/postgres"
    )


def test_database_url_template_requires_password(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:{DATABASE_PASSWORD}@db.example:5432/postgres",
    )
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)

    with pytest.raises(ValidationError, match="DATABASE_PASSWORD is required"):
        Settings(_env_file=None)


def test_database_urls_without_placeholder_remain_unchanged():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://postgres:encoded@db.example:5432/postgres",
        database_url_sync="postgresql+psycopg2://postgres:encoded@db.example:5432/postgres",
    )

    assert settings.database_url.endswith("postgres:encoded@db.example:5432/postgres")
    assert settings.database_url_sync.endswith(
        "postgres:encoded@db.example:5432/postgres"
    )
