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
    # FIX ([PLUGIN] subsystem audit): previously constructed a DaemonClient
    # with no transport, then monkeypatched client._request with a
    # duplicated, divergent reimplementation — even though the class's own
    # docstring explicitly says the transport constructor parameter exists
    # so "tests can exercise this class's real request/error handling
    # logic against an httpx.MockTransport ... rather than monkeypatching
    # private methods". The monkeypatch had drifted from the real
    # _request (missing its malformed-JSON handling entirely), so no test
    # using this helper was actually verifying _request's real behavior —
    # only a stale copy of it. Using the constructor's intended injection
    # point instead means every test below now exercises the actual
    # _request implementation.
    return DaemonClient(
        "https://node1.example.com:8443", "node-1", SECRET, transport=transport
    )


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

    # FIX ([PLUGIN] subsystem audit): this test previously had its own
    # third, separate monkeypatch of _request — dead code (a
    # `raising_request` helper defined and never called), plus yet another
    # reimplementation of the try/except this test's own comment claimed
    # to be testing the real one for. None of it actually exercised
    # DaemonClient._request's real httpx.RequestError handling. Using the
    # corrected _client_with_transport (constructor's transport=
    # injection, matching the class's own documented test-support design)
    # actually does.
    client = _client_with_transport(httpx.MockTransport(handler))
    with pytest.raises(DaemonError) as exc_info:
        await client.state("srv-1")
    assert "could not reach daemon" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malformed_json_response_raises_daemon_error():
    """FIX ([PLUGIN] subsystem audit): _request previously let a raw
    json.JSONDecodeError escape on a 2xx response with malformed content,
    breaking DaemonError's documented "any failure" contract. First test
    for this path."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not valid json{{{")

    client = _client_with_transport(httpx.MockTransport(handler))
    with pytest.raises(DaemonError) as exc_info:
        await client.state("srv-1")
    assert "malformed JSON" in str(exc_info.value)
    assert exc_info.value.status_code == 200
