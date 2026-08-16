"""
tests/test_model_router.py - Tests for services/ai/model_router.py.

ProviderFactory.build is monkeypatched to return scriptable fake providers
(success/failure per call), so these tests exercise the router's own
selection/failover/health-tracking logic without any real network call -
the providers themselves are already independently tested
(tests/test_ai_providers.py).
"""
from datetime import datetime, timedelta, timezone

import pytest

import services.settings_service as settings_service_module
from config import get_settings
from models.ai import AIModelConfig
from services.ai.base import GenerationResult, ProviderError
from services.ai.model_router import ModelRouter, NoAvailableModelError
from services.ai.provider_factory import ProviderFactory
from services.settings_service import SettingsService


@pytest.fixture(autouse=True)
def temp_env_file(tmp_path, monkeypatch):
    """Protects this project's real .env from test-value pollution — see
    the identical fixture in tests/test_provider_factory.py for why."""
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.setattr(settings_service_module, "ENV_PATH", env_file)
    return env_file


class FakeProvider:
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self._should_fail = should_fail
        self.call_count = 0

    async def generate(self, model, system_prompt, user_prompt, max_tokens=1024, temperature=0.7):
        self.call_count += 1
        if self._should_fail:
            raise ProviderError(f"simulated failure from {self.name}")
        return GenerationResult(text=f"response from {self.name}/{model}", model_name=model, latency_ms=42)


async def _enable_and_key(db, provider: str, enabled: bool = True, key: str = "sk-test"):
    enabled_setting = f"ai.{provider}_enabled"
    await SettingsService.update(db, enabled_setting, "true" if enabled else "false", actor="test")
    key_setting = {
        "openrouter": "ai.openrouter_key",
        "anthropic": "ai.anthropic_api_key",
        "gemini": "ai.gemini_api_key",
    }[provider]
    await SettingsService.update(db, key_setting, key, actor="test")


async def _add_config(db, provider: str, model_name: str, task_type: str, priority: int = 100) -> AIModelConfig:
    config = AIModelConfig(provider=provider, model_name=model_name, task_type=task_type, priority=priority)
    db.add(config)
    await db.flush()
    return config


@pytest.mark.asyncio
async def test_no_candidates_configured_raises_clear_error(db_session):
    async with db_session() as db:
        with pytest.raises(NoAvailableModelError, match="no eligible candidates configured"):
            await ModelRouter.generate(db, "moderation.review", "sys", "user")


@pytest.mark.asyncio
async def test_selects_highest_priority_candidate_first(db_session, monkeypatch):
    async with db_session() as db:
        await _enable_and_key(db, "anthropic")
        await _enable_and_key(db, "openrouter")
        await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        await _add_config(db, "openrouter", "some-model", "chat", priority=50)
        await db.commit()

        fake_anthropic = FakeProvider("anthropic")
        fake_openrouter = FakeProvider("openrouter")

        async def fake_build(db, provider_name):
            return {"anthropic": fake_anthropic, "openrouter": fake_openrouter}[provider_name]

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        routed = await ModelRouter.generate(db, "chat", "sys", "user")
        assert routed.provider == "anthropic"
        assert fake_anthropic.call_count == 1
        assert fake_openrouter.call_count == 0


@pytest.mark.asyncio
async def test_fails_over_to_next_candidate_on_failure(db_session, monkeypatch):
    async with db_session() as db:
        await _enable_and_key(db, "anthropic")
        await _enable_and_key(db, "openrouter")
        await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        await _add_config(db, "openrouter", "some-model", "chat", priority=50)
        await db.commit()

        fake_anthropic = FakeProvider("anthropic", should_fail=True)
        fake_openrouter = FakeProvider("openrouter", should_fail=False)

        async def fake_build(db, provider_name):
            return {"anthropic": fake_anthropic, "openrouter": fake_openrouter}[provider_name]

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        routed = await ModelRouter.generate(db, "chat", "sys", "user")
        assert routed.provider == "openrouter"
        assert fake_anthropic.call_count == 1
        assert fake_openrouter.call_count == 1


@pytest.mark.asyncio
async def test_marks_unhealthy_after_threshold_consecutive_failures(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_model_unhealthy_after_failures", 2)

    async with db_session() as db:
        await _enable_and_key(db, "anthropic")
        config = await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        await db.commit()
        config_id = config.id

        fake_anthropic = FakeProvider("anthropic", should_fail=True)

        async def fake_build(db, provider_name):
            return fake_anthropic

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        for _ in range(2):
            with pytest.raises(NoAvailableModelError):
                await ModelRouter.generate(db, "chat", "sys", "user")
        await db.commit()

        refreshed = await db.get(AIModelConfig, config_id)
        assert refreshed.consecutive_failures == 2
        assert refreshed.is_healthy is False


@pytest.mark.asyncio
async def test_unhealthy_candidate_is_skipped_within_cooldown(db_session, monkeypatch):
    async with db_session() as db:
        await _enable_and_key(db, "anthropic")
        config = await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        config.is_healthy = False
        config.last_failure_at = datetime.now(timezone.utc)  # just failed
        await db.commit()

        fake_anthropic = FakeProvider("anthropic", should_fail=False)

        async def fake_build(db, provider_name):
            return fake_anthropic

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        with pytest.raises(NoAvailableModelError):
            await ModelRouter.generate(db, "chat", "sys", "user")
        assert fake_anthropic.call_count == 0  # never even tried — still in cooldown


@pytest.mark.asyncio
async def test_unhealthy_candidate_retried_after_cooldown_elapses(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_model_health_cooldown_seconds", 60)

    async with db_session() as db:
        await _enable_and_key(db, "anthropic")
        config = await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        config.is_healthy = False
        config.last_failure_at = datetime.now(timezone.utc) - timedelta(seconds=120)  # long past cooldown
        await db.commit()

        fake_anthropic = FakeProvider("anthropic", should_fail=False)

        async def fake_build(db, provider_name):
            return fake_anthropic

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        routed = await ModelRouter.generate(db, "chat", "sys", "user")
        assert routed.provider == "anthropic"
        assert fake_anthropic.call_count == 1


@pytest.mark.asyncio
async def test_successful_call_resets_failure_count_and_marks_healthy(db_session, monkeypatch):
    async with db_session() as db:
        await _enable_and_key(db, "anthropic")
        config = await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        config.consecutive_failures = 1
        config.is_healthy = True
        await db.commit()
        config_id = config.id

        fake_anthropic = FakeProvider("anthropic", should_fail=False)

        async def fake_build(db, provider_name):
            return fake_anthropic

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        await ModelRouter.generate(db, "chat", "sys", "user")
        await db.commit()

        refreshed = await db.get(AIModelConfig, config_id)
        assert refreshed.consecutive_failures == 0
        assert refreshed.is_healthy is True
        assert refreshed.last_latency_ms == 42


@pytest.mark.asyncio
async def test_disabled_provider_is_skipped_even_with_a_configured_model_row(db_session, monkeypatch):
    async with db_session() as db:
        # Model row exists, but the provider itself is disabled.
        await _enable_and_key(db, "anthropic", enabled=False)
        await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        await db.commit()

        called = {"count": 0}

        async def fake_build(db, provider_name):
            called["count"] += 1
            return FakeProvider("anthropic")

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        with pytest.raises(NoAvailableModelError):
            await ModelRouter.generate(db, "chat", "sys", "user")
        assert called["count"] == 0  # never even reached build() — filtered out earlier


@pytest.mark.asyncio
async def test_exclude_providers_skips_named_provider(db_session, monkeypatch):
    async with db_session() as db:
        await _enable_and_key(db, "anthropic")
        await _enable_and_key(db, "openrouter")
        await _add_config(db, "anthropic", "claude-x", "chat", priority=10)
        await _add_config(db, "openrouter", "some-model", "chat", priority=50)
        await db.commit()

        fake_openrouter = FakeProvider("openrouter")

        async def fake_build(db, provider_name):
            assert provider_name != "anthropic"
            return fake_openrouter

        monkeypatch.setattr(ProviderFactory, "build", fake_build)

        routed = await ModelRouter.generate(db, "chat", "sys", "user", exclude_providers={"anthropic"})
        assert routed.provider == "openrouter"
