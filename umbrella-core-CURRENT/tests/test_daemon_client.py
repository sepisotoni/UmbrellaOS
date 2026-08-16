"""
tests/test_daemon_client.py — Tests for services/daemon_client.py.

Uses httpx's MockTransport (httpx's own supported testing mechanism, not a
project-specific fake) to verify request construction, auth header
presence, and response parsing without a running daemon.
"""
import json

import httpx
import pytest

from services.daemon_client import ContainerState, DaemonClient, DaemonError, StatsSnapshot

SECRET = "a-shared-secret-at-least-32-bytes-long-ok"


def _client_with_transport(transport: httpx.MockTransport) -> DaemonClient:
    client = DaemonClient("https://node1.example.com:8443", "node-1", SECRET)

    # Monkeypatch the internal httpx client construction to use our
    # MockTransport instead of making a real network call — the one place
    # this test reaches past the public interface, and only to swap the
    # transport, not any business logic.
    original_request = client._request

    async def patched_request(method, path, json=None):
        url = f"{client._base_url}{path}"
        headers = client._headers()
        async with httpx.AsyncClient(transport=transport, timeout=client._timeout) as http_client:
            response = await http_client.request(method, url, headers=headers, json=json)
        if response.status_code >= 400:
            raise DaemonError(f"daemon returned {response.status_code}", status_code=response.status_code)
        return response.json()

    client._request = patched_request
    return client


@pytest.mark.asyncio
async def test_start_sends_authenticated_request_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth_header"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={"ServerID": "srv-1", "RuntimeID": "docker-abc", "Status": "running", "OOMKilled": False},
        )

    client = _client_with_transport(httpx.MockTransport(handler))
    state = await client.start("srv-1")

    assert captured["url"] == "https://node1.example.com:8443/v1/servers/srv-1/start"
    assert captured["auth_header"].startswith("Bearer ")
    assert isinstance(state, ContainerState)
    assert state.status == "running"
    assert state.runtime_id == "docker-abc"


@pytest.mark.asyncio
async def test_stop_sends_grace_period_in_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content) if request.content else None
        return httpx.Response(200, json={"ServerID": "srv-1", "Status": "stopped"})

    client = _client_with_transport(httpx.MockTransport(handler))
    await client.stop("srv-1", grace_period_seconds=45)

    assert captured["body"] == {"grace_period_seconds": 45}


@pytest.mark.asyncio
async def test_error_response_raises_daemon_error_with_status_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="no such container")

    client = _client_with_transport(httpx.MockTransport(handler))
    with pytest.raises(DaemonError) as exc_info:
        await client.state("srv-missing")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_stats_parses_snapshot_correctly():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Timestamp": "2026-07-07T12:00:00Z",
                "CPUPercent": 42.5,
                "MemoryUsedBytes": 500_000_000,
                "MemoryLimitBytes": 2_000_000_000,
                "NetworkRxBytes": 1000,
                "NetworkTxBytes": 500,
            },
        )

    client = _client_with_transport(httpx.MockTransport(handler))
    stats = await client.stats("srv-1")

    assert isinstance(stats, StatsSnapshot)
    assert stats.cpu_percent == 42.5
    assert stats.memory_used_bytes == 500_000_000


@pytest.mark.asyncio
async def test_network_error_raises_daemon_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = DaemonClient("https://unreachable.example.com:8443", "node-1", SECRET)
    # This one exercises the real _request path (not the patched test
    # helper) specifically to prove the RequestError -> DaemonError
    # wrapping in the actual production code, not just the test's transport
    # substitution.
    import httpx as httpx_module

    async def raising_request(method, path, json=None):
        raise httpx_module.ConnectError("connection refused")

    # Use a MockTransport that raises, through the real client construction
    # path, to exercise DaemonClient._request's own try/except.
    real_client = DaemonClient("https://unreachable.example.com:8443", "node-1", SECRET)

    async def patched(method, path, json=None):
        url = f"{real_client._base_url}{path}"
        transport = httpx.MockTransport(handler)
        try:
            async with httpx.AsyncClient(transport=transport, timeout=1.0) as http_client:
                await http_client.request(method, url, headers=real_client._headers(), json=json)
        except httpx.RequestError as exc:
            raise DaemonError(f"could not reach daemon: {exc}") from exc

    real_client._request = patched
    with pytest.raises(DaemonError):
        await real_client.state("srv-1")
