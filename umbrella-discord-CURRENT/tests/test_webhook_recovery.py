from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.cogs import webhook_cog
from bot.cogs.webhook_cog import WebhookCog
from bot.services.umbrella_core_client import UmbrellaCoreError
from bot.webhook_server import WebhookServer


@pytest.mark.asyncio
async def test_webhook_registration_retries_with_bounded_backoff(monkeypatch, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr(webhook_cog, "_REGISTRATION_RETRY_DELAYS", (0, 0, 0))
    calls = 0

    async def register_bot(callback_url):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise UmbrellaCoreError("temporary core failure")

    cog = WebhookCog(SimpleNamespace(core=SimpleNamespace(register_bot=register_bot)))

    registered = await cog._register_with_backoff("https://bot.example/webhook")

    assert registered
    assert calls == 3
    assert "retrying" in caplog.text
    assert "Registered bot webhook" in caplog.text


@pytest.mark.asyncio
async def test_webhook_registration_exhaustion_is_observable(monkeypatch, caplog):
    monkeypatch.setattr(webhook_cog, "_REGISTRATION_RETRY_DELAYS", (0, 0, 0))
    monkeypatch.setattr(webhook_cog, "_REGISTRATION_RETRY_INTERVAL", 0)
    calls = 0

    async def register_bot(callback_url):
        nonlocal calls
        calls += 1
        raise UmbrellaCoreError("core unavailable")

    cog = WebhookCog(SimpleNamespace(core=SimpleNamespace(register_bot=register_bot)))

    registered = await cog._register_with_backoff("https://bot.example/webhook")

    assert not registered
    assert calls == 4
    assert "failed after 4 attempts" in caplog.text


@pytest.mark.asyncio
async def test_webhook_handler_exception_is_acknowledged_with_2xx(caplog):
    server = WebhookServer(shared_secret="test")
    server._verify_mac_async = AsyncMock(return_value=True)

    async def fail_handler(payload):
        raise RuntimeError("handler failed")

    server.register_handler("bridge.dashboard_message", fail_handler)

    async def json_body():
        return {"event": "bridge.dashboard_message", "payload": {}}

    request = SimpleNamespace(
        headers={"X-Auth-MAC": "valid", "X-Auth-Timestamp": "1"},
        json=json_body,
    )

    response = await server._handle_webhook(request)

    assert response.status == 200
    assert "handler error" in response.text
    assert "handler failed" in caplog.text
