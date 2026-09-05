"""
tests/test_umbrella_core_client.py — Tests for
bot/services/umbrella_core_client.py, using httpx.MockTransport (no real
network, no real umbrella-core instance needed) - same pattern
umbrella-core's own tests/test_ai_providers.py uses for its HTTP-based
providers.
"""
import json

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
        return httpx.Response(200, json={"investigation_id": "inv-1", "summary": "all clear", "confidence": 0.9, "findings": []})

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    result = await client.invoke("investigation.run", {"question": "why is it slow", "target_user_id": None})
    assert result["investigation_id"] == "inv-1"


@pytest.mark.asyncio
async def test_invoke_raises_umbrella_core_error_on_permission_denied():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"success": False, "error": "Missing permission: investigation.run", "code": "PERMISSION_DENIED", "status": 403, "timestamp": "now"})

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(UmbrellaCoreError, match="Missing permission"):
        await client.invoke("investigation.run", {})


@pytest.mark.asyncio
async def test_invoke_error_exposes_status_code_and_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"success": False, "error": "Moderation report not found: xyz", "code": "NOT_FOUND", "status": 404, "timestamp": "now"})

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(UmbrellaCoreError) as exc_info:
        await client.invoke("moderation_intelligence.report.get", {"report_id": "xyz"})
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_invoke_raises_on_network_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(UmbrellaCoreError, match="Could not reach umbrella-core"):
        await client.invoke("investigation.run", {})


@pytest.mark.asyncio
async def test_invoke_handles_non_json_error_body_gracefully():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(UmbrellaCoreError, match="Bad Gateway"):
        await client.invoke("investigation.run", {})


@pytest.mark.asyncio
async def test_list_capabilities_returns_list():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v1/capabilities"
        return httpx.Response(200, json=[{"name": "investigation.run", "summary": "..."}])

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    result = await client.list_capabilities()
    assert result[0]["name"] == "investigation.run"


@pytest.mark.asyncio
async def test_base_url_trailing_slash_is_stripped():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/capabilities/x/invoke"
        return httpx.Response(200, json={})

    client = UmbrellaCoreClient("https://core.example.com/", "test-key", transport=httpx.MockTransport(handler))
    await client.invoke("x", {})


@pytest.mark.asyncio
async def test_invoke_sends_discord_user_id_header_when_given():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-discord-user-id"] == "123456"
        return httpx.Response(200, json={"ok": True})

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    await client.invoke("investigation.run", {}, discord_user_id="123456")


@pytest.mark.asyncio
async def test_invoke_omits_discord_user_id_header_by_default():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "x-discord-user-id" not in request.headers
        return httpx.Response(200, json={"ok": True})

    client = UmbrellaCoreClient("https://core.example.com", "test-key", transport=httpx.MockTransport(handler))
    await client.invoke("investigation.run", {})
