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
            pipe_console(
                client_ws,
                upstream_url,
                "node-1",
                "a-signing-secret-at-least-32-bytes-long",
            )
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
            pipe_console(
                client_ws,
                upstream_url,
                "node-1",
                "a-signing-secret-at-least-32-bytes-long",
            )
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
    await pipe_console(
        client_ws,
        "ws://localhost:1",
        "node-1",
        "a-signing-secret-at-least-32-bytes-long",
    )
    assert client_ws.closed is True


@pytest.mark.asyncio
async def test_pipe_console_view_only_cannot_forward_commands():
    """A viewer may connect but their input must never reach the daemon."""
    received_by_daemon = []

    async def fake_daemon_handler(connection):
        async for message in connection:
            received_by_daemon.append(message)

    async with websockets.serve(fake_daemon_handler, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client_ws = FakeClientWS(to_send=[b"stop\n"])
        await asyncio.wait_for(
            pipe_console(
                client_ws,
                f"ws://localhost:{port}",
                "node-1",
                "a-signing-secret-at-least-32-bytes-long",
                allow_client_input=False,
            ),
            timeout=2.0,
        )

    assert received_by_daemon == []
    assert client_ws.closed is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("permissions", "can_write"),
    [
        ({"hosting.server.view"}, False),
        ({"hosting.server.view", "hosting.server.control"}, True),
    ],
)
async def test_proxy_console_grants_write_only_with_control(
    monkeypatch, permissions, can_write
):
    """Verify the route passes RBAC decision into the proxy, not just pipe defaults."""
    from types import SimpleNamespace
    import api.routers.hosting_console_ws as console_module

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, model, server_id):
            return SimpleNamespace(node_id="node-1")

    class FakeSocket:
        accepted = False

        async def accept(self):
            self.accepted = True

        async def close(self, **kwargs):
            raise AssertionError("Authorized viewer should not be rejected")

    async def fake_get_user(token, session):
        return SimpleNamespace(id="viewer-1")

    async def fake_permissions(user, session):
        return permissions

    async def fake_get_node(session, node_id):
        return SimpleNamespace(id=node_id, daemon_url="https://daemon.example")

    calls = []

    async def fake_pipe(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(console_module, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(console_module, "get_current_user", fake_get_user)
    monkeypatch.setattr(console_module, "resolve_user_permissions", fake_permissions)
    monkeypatch.setattr(console_module.NodeService, "get_node", fake_get_node)
    monkeypatch.setattr(
        console_module.NodeService, "decrypted_signing_secret", lambda node: "secret"
    )
    monkeypatch.setattr(console_module, "pipe_console", fake_pipe)
    ws = FakeSocket()
    await console_module.proxy_console(ws, "srv-1", token="fake-token")

    assert ws.accepted is True
    assert len(calls) == 1
    assert calls[0][1]["allow_client_input"] is can_write
