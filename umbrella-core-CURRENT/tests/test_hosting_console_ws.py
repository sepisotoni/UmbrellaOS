"""
tests/test_hosting_console_ws.py — Tests for api/routers/hosting_console_ws.py.

`pipe_console` is tested against a genuine local `websockets` server (not a
fake) standing in for a node's daemon — a real WebSocket server, just a
small scripted one, the same class of infrastructure test double used
throughout this project. The route handler's auth/DB-lookup glue is not
re-tested here since it delegates entirely to functions already covered
elsewhere (get_current_user, resolve_user_permissions, NodeService.get_node)
— see the module docstring in hosting_console_ws.py for why that split
makes this a reasonable test boundary rather than a gap.
"""
import asyncio

import pytest
import websockets

from api.routers.hosting_console_ws import daemon_ws_url, pipe_console


def test_daemon_ws_url_translates_https_to_wss():
    url = daemon_ws_url("https://node1.example.com:8443", "srv-1")
    assert url == "wss://node1.example.com:8443/v1/servers/srv-1/console"


def test_daemon_ws_url_translates_http_to_ws():
    url = daemon_ws_url("http://node1.local:8443", "srv-1")
    assert url == "ws://node1.local:8443/v1/servers/srv-1/console"


def test_daemon_ws_url_strips_trailing_slash():
    url = daemon_ws_url("https://node1.example.com:8443/", "srv-1")
    assert url == "wss://node1.example.com:8443/v1/servers/srv-1/console"


class FakeClientWS:
    """
    A minimal double for FastAPI's WebSocket, implementing only the subset
    pipe_console actually uses (receive_bytes/send_bytes/close) — a real
    dashboard browser connection is what this stands in for in this test;
    the actual daemon side of the proxy is a genuine local WS server, not
    faked.
    """

    def __init__(self, to_send: list[bytes]):
        self._to_send = list(to_send)
        self.received: list[bytes] = []
        self.closed = False

    async def receive_bytes(self) -> bytes:
        if self._to_send:
            return self._to_send.pop(0)
        # No more scripted client messages — block "forever" (until the
        # test cancels this side via the daemon closing first).
        await asyncio.sleep(3600)
        raise AssertionError("unreachable")

    async def send_bytes(self, data: bytes) -> None:
        self.received.append(data)

    async def close(self, code: int | None = None) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_pipe_console_forwards_daemon_output_to_client():
    received_by_daemon = []

    async def fake_daemon_handler(connection):
        await connection.send(b"hello from daemon")
        async for message in connection:
            received_by_daemon.append(message)

    async with websockets.serve(fake_daemon_handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        upstream_url = f"ws://localhost:{port}"

        client_ws = FakeClientWS(to_send=[])
        # Run with a timeout — the daemon side never explicitly closes in
        # this handler, so pipe_console would otherwise run until the
        # client side is cancelled; bound it so a stuck proxy fails the
        # test instead of hanging CI.
        task = asyncio.create_task(
            pipe_console(client_ws, upstream_url, "node-1", "a-signing-secret-at-least-32-bytes-long")
        )
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert b"hello from daemon" in client_ws.received


@pytest.mark.asyncio
async def test_pipe_console_forwards_client_input_to_daemon():
    received_by_daemon = []
    daemon_got_message = asyncio.Event()

    async def fake_daemon_handler(connection):
        async for message in connection:
            received_by_daemon.append(message)
            daemon_got_message.set()

    async with websockets.serve(fake_daemon_handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        upstream_url = f"ws://localhost:{port}"

        client_ws = FakeClientWS(to_send=[b"say hello\n"])
        task = asyncio.create_task(
            pipe_console(client_ws, upstream_url, "node-1", "a-signing-secret-at-least-32-bytes-long")
        )
        try:
            await asyncio.wait_for(daemon_got_message.wait(), timeout=2.0)
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    assert received_by_daemon == [b"say hello\n"]


@pytest.mark.asyncio
async def test_pipe_console_closes_client_gracefully_when_daemon_unreachable():
    client_ws = FakeClientWS(to_send=[])
    # Port 1 on localhost: nothing listens there, connection refused fast.
    await pipe_console(client_ws, "ws://localhost:1", "node-1", "a-signing-secret-at-least-32-bytes-long")
    assert client_ws.closed is True
