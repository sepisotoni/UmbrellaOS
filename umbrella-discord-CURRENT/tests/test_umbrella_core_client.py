"""
tests/test_umbrella_core_client.py — Tests for
bot/services/umbrella_core_client.py, using httpx.MockTransport (no real
network, no real umbrella-core instance needed) - same pattern
umbrella-core's own tests/test_ai_providers.py uses for its HTTP-based
providers.
"""

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.services.umbrella_core_client import UmbrellaCoreClient, UmbrellaCoreError


@pytest.mark.asyncio
async def test_invoke_success_returns_result_dict():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "x-auth-mac" in request.headers
        assert "x-auth-timestamp" in request.headers
        assert request.url.path == "/api/v1/capabilities/investigation.run/invoke"
        body = json.loads(request.content)
        assert body == {"question": "why is it slow", "target_user_id": None}
        return httpx.Response(
            200,
            json={
                "investigation_id": "inv-1",
                "summary": "all clear",
                "confidence": 0.9,
                "findings": [],
            },
        )

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    result = await client.invoke(
        "investigation.run", {"question": "why is it slow", "target_user_id": None}
    )
    assert result["investigation_id"] == "inv-1"


@pytest.mark.asyncio
async def test_invoke_raises_umbrella_core_error_on_permission_denied():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "success": False,
                "error": "Missing permission: investigation.run",
                "code": "PERMISSION_DENIED",
                "status": 403,
                "timestamp": "now",
            },
        )

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(UmbrellaCoreError, match="Missing permission"):
        await client.invoke("investigation.run", {})


@pytest.mark.asyncio
async def test_invoke_error_exposes_status_code_and_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "success": False,
                "error": "Moderation report not found: xyz",
                "code": "NOT_FOUND",
                "status": 404,
                "timestamp": "now",
            },
        )

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(UmbrellaCoreError) as exc_info:
        await client.invoke("moderation_intelligence.report.get", {"report_id": "xyz"})
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_invoke_raises_on_network_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(UmbrellaCoreError, match="Could not reach umbrella-core"):
        await client.invoke("investigation.run", {})


@pytest.mark.asyncio
async def test_invoke_handles_non_json_error_body_gracefully():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(UmbrellaCoreError, match="Bad Gateway"):
        await client.invoke("investigation.run", {})


@pytest.mark.asyncio
async def test_list_capabilities_returns_list():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/capabilities"
        return httpx.Response(
            200, json=[{"name": "investigation.run", "summary": "..."}]
        )

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    result = await client.list_capabilities()
    assert result[0]["name"] == "investigation.run"


@pytest.mark.asyncio
async def test_base_url_trailing_slash_is_stripped():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/capabilities/x/invoke"
        return httpx.Response(200, json={})

    client = UmbrellaCoreClient(
        "https://core.example.com/", "test-key", transport=httpx.MockTransport(handler)
    )
    await client.invoke("x", {})


@pytest.mark.asyncio
async def test_bot_runtime_state_sends_revisions_and_returns_changes():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/bot/runtime-state"
        assert dict(request.url.params) == {
            "config_revision": "config-v1",
            "token_revision": "token-v1",
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "changed": True,
                "config_revision": "config-v2",
                "token_revision": "token-v1",
                "config": {"remote": {}, "guilds": []},
            },
        )

    client = UmbrellaCoreClient(
        "https://core.example.com",
        "test-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.get_bot_runtime_state(
        config_revision="config-v1",
        token_revision="token-v1",
    )

    assert result is not None
    assert result["config_revision"] == "config-v2"
    assert "discord_token" not in result


@pytest.mark.asyncio
async def test_bot_runtime_state_returns_none_when_unchanged():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/bot/runtime-state"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "changed": False,
                "config_revision": "config-v1",
                "token_revision": "token-v1",
            },
        )

    client = UmbrellaCoreClient(
        "https://core.example.com",
        "test-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.get_bot_runtime_state(
        config_revision="config-v1",
        token_revision="token-v1",
    )

    assert result is None


@pytest.mark.asyncio
async def test_bot_runtime_state_returns_pending_events_even_without_config_changes():
    pending = [
        {
            "id": "delivery-1",
            "event": "bridge.dashboard_message",
            "payload": {"message_id": 1},
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "changed": True,
                "config_revision": "config-v1",
                "token_revision": "token-v1",
                "pending_events": pending,
            },
        )

    client = UmbrellaCoreClient(
        "https://core.example.com",
        "test-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.get_bot_runtime_state(
        config_revision="config-v1",
        token_revision="token-v1",
    )

    assert result is not None
    assert result["pending_events"] == pending


@pytest.mark.asyncio
async def test_register_bot_returns_callback_verification_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/bot/register"
        assert json.loads(request.content) == {
            "callback_url": "https://bot.example/webhook"
        }
        return httpx.Response(200, json={"callback_verified": True})

    client = UmbrellaCoreClient(
        "https://core.example.com",
        "test-key",
        transport=httpx.MockTransport(handler),
    )
    client._make_auth_headers_async = AsyncMock(return_value={})

    assert await client.register_bot("https://bot.example/webhook") is True


@pytest.mark.asyncio
async def test_acknowledge_bot_event_reports_core_acknowledgement():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/bot/events/delivery-1/ack"
        return httpx.Response(200, json={"ok": True, "acknowledged": True})

    client = UmbrellaCoreClient(
        "https://core.example.com",
        "test-key",
        transport=httpx.MockTransport(handler),
    )
    client._make_auth_headers_async = AsyncMock(return_value={})

    assert await client.acknowledge_bot_event("delivery-1") is True


@pytest.mark.asyncio
async def test_invoke_sends_discord_user_id_header_when_given():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-discord-user-id"] == "123456"
        return httpx.Response(200, json={"ok": True})

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    await client.invoke("investigation.run", {}, discord_user_id="123456")


@pytest.mark.asyncio
async def test_invoke_omits_discord_user_id_header_by_default():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "x-discord-user-id" not in request.headers
        return httpx.Response(200, json={"ok": True})

    client = UmbrellaCoreClient(
        "https://core.example.com", "test-key", transport=httpx.MockTransport(handler)
    )
    await client.invoke("investigation.run", {})


@pytest.mark.asyncio
async def test_sync_guilds_posts_all_guilds_and_returns_per_guild_config():
    guilds = [
        {"guild_id": "123", "name": "Community", "channels": [], "roles": []},
        {"guild_id": "456", "name": "Staff", "channels": [], "roles": []},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/bot/guilds/sync"
        assert json.loads(request.content) == {"guilds": guilds}
        return httpx.Response(
            200,
            json={"guilds": [{**guilds[0], "owner_role_id": None}]},
        )

    client = UmbrellaCoreClient(
        "https://core.example.com",
        "test-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.sync_guilds(guilds)

    assert result[0]["guild_id"] == "123"
