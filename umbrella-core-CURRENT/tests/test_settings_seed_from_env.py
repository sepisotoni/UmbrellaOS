"""
tests/test_settings_seed_from_env.py — Tests for the SEED_FROM_ENV
boot-time gating and auto-reset behavior in SettingsService.seed_defaults.

Monkeypatches services.settings_service.ENV_PATH to a temp file rather than
letting `set_key` write into the project's real .env during a test run.
"""
import pytest
from sqlalchemy import select

from config import get_settings
from models.setting import Setting
import services.settings_service as settings_service_module
from services.settings_service import SettingsService


@pytest.fixture
def temp_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.setattr(settings_service_module, "ENV_PATH", env_file)
    return env_file


@pytest.mark.asyncio
async def test_seed_defaults_does_not_sync_from_env_when_flag_is_false(db_session, temp_env_file, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "seed_from_env", False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-should-not-be-pulled-in")

    async with db_session() as db:
        await SettingsService.seed_defaults(db)
        row = await db.scalar(select(Setting).where(Setting.key == "ai.openrouter_key"))
        assert row.value == ""  # never synced, since the flag was off


@pytest.mark.asyncio
async def test_seed_defaults_gap_fills_from_env_when_flag_is_true(db_session, temp_env_file, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "seed_from_env", True)
    monkeypatch.setattr(settings, "force_env_override", False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-env-file")

    async with db_session() as db:
        await SettingsService.seed_defaults(db)
        row = await db.scalar(select(Setting).where(Setting.key == "ai.openrouter_key"))
        assert row.value == "sk-from-env-file"


@pytest.mark.asyncio
async def test_seed_defaults_never_overwrites_existing_dashboard_value_in_gap_fill_mode(
    db_session, temp_env_file, monkeypatch
):
    settings = get_settings()
    monkeypatch.setattr(settings, "seed_from_env", True)
    monkeypatch.setattr(settings, "force_env_override", False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-env-file")

    async with db_session() as db:
        # Simulate a value already set via the dashboard before this boot.
        await SettingsService.seed_defaults(db)
        await SettingsService.update(db, "ai.openrouter_key", "sk-set-via-dashboard", actor="test")

    async with db_session() as db:
        await SettingsService.seed_defaults(db)  # a second "boot" with the flag still true
        row = await db.scalar(select(Setting).where(Setting.key == "ai.openrouter_key"))
        # Gap-fill must never clobber a real, already-set value.
        assert row.value == "sk-set-via-dashboard"


@pytest.mark.asyncio
async def test_seed_defaults_auto_resets_seed_from_env_flag_in_env_file(db_session, temp_env_file, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "seed_from_env", True)
    monkeypatch.setattr(settings, "force_env_override", False)

    async with db_session() as db:
        await SettingsService.seed_defaults(db)

    content = temp_env_file.read_text()
    assert "SEED_FROM_ENV=false" in content or "SEED_FROM_ENV='false'" in content


@pytest.mark.asyncio
async def test_seed_defaults_force_override_also_resets_itself(db_session, temp_env_file, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "seed_from_env", True)
    monkeypatch.setattr(settings, "force_env_override", True)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-forced-value")

    async with db_session() as db:
        await SettingsService.seed_defaults(db)
        await db.commit()

        # Force mode overwrites even an already-set value.
        row = await db.scalar(select(Setting).where(Setting.key == "ai.openrouter_key"))
        assert row.value == "sk-forced-value"

    content = temp_env_file.read_text()
    assert "SEED_FROM_ENV=false" in content or "SEED_FROM_ENV='false'" in content
    assert "FORCE_ENV_OVERRIDE=false" in content or "FORCE_ENV_OVERRIDE='false'" in content
