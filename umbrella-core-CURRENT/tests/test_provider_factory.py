"""
tests/test_provider_factory.py - Tests for services/ai/provider_factory.py:
proves providers are actually toggled on/off and keyed from the DB-backed
Setting model, which is what makes them dashboard-configurable at runtime.
"""
import pytest

import services.settings_service as settings_service_module
from services.ai.base import ProviderError
from services.ai.provider_factory import ProviderFactory
from services.ai.anthropic_provider import AnthropicProvider
from services.settings_service import SettingsService


@pytest.fixture(autouse=True)
def temp_env_file(tmp_path, monkeypatch):
    """
    SettingsService.update() writes mapped keys (ai.anthropic_api_key,
    ai.openrouter_key, ai.gemini_api_key) back into .env on every call —
    exactly the dashboard-sync behavior these tests are implicitly
    exercising. Autouse here so every test in this file writes into a
    throwaway temp file instead of this project's real .env.
    """
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.setattr(settings_service_module, "ENV_PATH", env_file)
    return env_file


@pytest.mark.asyncio
async def test_build_fails_for_unknown_provider(db_session):
    async with db_session() as db:
        with pytest.raises(ProviderError, match="unknown"):
            await ProviderFactory.build(db, "does-not-exist")


@pytest.mark.asyncio
async def test_build_fails_when_disabled(db_session):
    async with db_session() as db:
        await SettingsService.update(db, "ai.anthropic_enabled", "false", actor="test")
        await SettingsService.update(db, "ai.anthropic_api_key", "sk-test-key", actor="test")
        with pytest.raises(ProviderError, match="disabled"):
            await ProviderFactory.build(db, "anthropic")


@pytest.mark.asyncio
async def test_build_fails_when_no_key_configured(db_session):
    async with db_session() as db:
        await SettingsService.update(db, "ai.anthropic_enabled", "true", actor="test")
        await SettingsService.update(db, "ai.anthropic_api_key", "", actor="test")
        with pytest.raises(ProviderError, match="no API key configured"):
            await ProviderFactory.build(db, "anthropic")


@pytest.mark.asyncio
async def test_build_succeeds_when_enabled_and_keyed(db_session):
    async with db_session() as db:
        await SettingsService.update(db, "ai.anthropic_enabled", "true", actor="test")
        await SettingsService.update(db, "ai.anthropic_api_key", "sk-real-looking-key", actor="test")
        provider = await ProviderFactory.build(db, "anthropic")
        assert isinstance(provider, AnthropicProvider)


@pytest.mark.asyncio
async def test_available_providers_reflects_toggles(db_session):
    async with db_session() as db:
        # Default seed state: openrouter enabled, anthropic enabled, gemini disabled
        # (see DEFAULT_SETTINGS) — but none have keys configured yet by default.
        available = await ProviderFactory.available_providers(db)
        assert available == []

        await SettingsService.update(db, "ai.anthropic_api_key", "sk-key", actor="test")
        available = await ProviderFactory.available_providers(db)
        assert available == ["anthropic"]

        await SettingsService.update(db, "ai.openrouter_key", "sk-or-key", actor="test")
        available = await ProviderFactory.available_providers(db)
        assert set(available) == {"anthropic", "openrouter"}


@pytest.mark.asyncio
async def test_toggling_a_provider_off_removes_it_from_available_immediately(db_session):
    async with db_session() as db:
        await SettingsService.update(db, "ai.anthropic_api_key", "sk-key", actor="test")
        assert "anthropic" in await ProviderFactory.available_providers(db)

        await SettingsService.update(db, "ai.anthropic_enabled", "false", actor="test")
        assert "anthropic" not in await ProviderFactory.available_providers(db)


@pytest.mark.asyncio
async def test_gemini_disabled_by_default(db_session):
    async with db_session() as db:
        await SettingsService.update(db, "ai.gemini_api_key", "sk-key", actor="test")
        # Even with a key configured, gemini's seeded default is disabled.
        assert "gemini" not in await ProviderFactory.available_providers(db)
        assert await ProviderFactory.is_enabled(db, "gemini") is False
