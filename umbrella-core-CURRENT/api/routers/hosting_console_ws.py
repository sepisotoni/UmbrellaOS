"""
api/routers/hosting_console_ws.py — Proxies a dashboard's WebSocket
console connection to the correct node's umbrella-daemon console endpoint.

This is the "event bus / WS gateway" piece ADR-0003 explicitly deferred
until Phase 3 had a real consumer (the dashboard) to build it against —
this router is that consumer's server-side counterpart: the dashboard
never talks to a node's daemon directly (it doesn't have node tokens, and
shouldn't), it talks to core, and core proxies.

Auth: browser WebSocket clients can't set arbitrary request headers, so the
session token travels as a query parameter (`?token=...`) rather than an
Authorization header — the standard, unavoidable pattern for
browser-originated WebSocket auth (the same reason dashboards elsewhere use
this pattern; it isn't an UmbrellaOS-specific compromise). The token is
validated exactly the same way as an HTTP Bearer session token
(`get_current_user`), just read from a different place.
"""
import asyncio
import logging

import websockets
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette import status as ws_status

from api.middleware.session import get_current_user
from database import AsyncSessionLocal
from models.hosting import Server
from services.node_auth_service import issue_node_token
from services.node_service import NodeService
from services.permission_resolution import resolve_user_permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/hosting", tags=["hosting-console"])

# Viewing console output is gated the same as any other read of a server's
# live state — there is no separate, stricter permission for sending
# commands into the console in this phase; that's a reasonable future
# tightening (e.g. a dedicated hosting.server.console_write) flagged here
# rather than silently assumed unnecessary.
REQUIRED_PERMISSION = "hosting.server.view"


def daemon_ws_url(daemon_url: str, server_id: str) -> str:
    """Translate a daemon's http(s) base URL into its ws(s) console endpoint."""
    if daemon_url.startswith("https://"):
        base = "wss://" + daemon_url[len("https://"):]
    elif daemon_url.startswith("http://"):
        base = "ws://" + daemon_url[len("http://"):]
    else:
        base = daemon_url
    return f"{base.rstrip('/')}/v1/servers/{server_id}/console"


@router.websocket("/servers/{server_id}/console")
async def proxy_console(websocket: WebSocket, server_id: str, token: str = Query(...)):
    async with AsyncSessionLocal() as db:
        try:
            user = await get_current_user(token, db)
        except Exception:
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION, reason="invalid or expired session token")
            return

        permissions = await resolve_user_permissions(user, db)
        if REQUIRED_PERMISSION not in permissions:
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION, reason="missing permission")
            return

        server = await db.get(Server, server_id)
        if server is None:
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION, reason="no such server")
            return

        node = await NodeService.get_node(db, server.node_id)

    await websocket.accept()
    decrypted_secret = NodeService.decrypted_signing_secret(node)
    await pipe_console(websocket, daemon_ws_url(node.daemon_url, server_id), node.id, decrypted_secret)


async def pipe_console(client_ws, upstream_url: str, node_id: str, signing_secret: str) -> None:
    """
    Open the outbound connection to the daemon and pipe bytes both
    directions until either side disconnects. Split out from the route
    handler so it's testable against a real local WebSocket server without
    needing the full auth/DB-lookup chain above (which delegates entirely
    to already-independently-tested functions: get_current_user,
    resolve_user_permissions, NodeService.get_node).
    """
    node_token = issue_node_token(node_id, signing_secret)
    try:
        async with websockets.connect(
            upstream_url, additional_headers={"Authorization": f"Bearer {node_token}"}
        ) as daemon_ws:
            forward_in = asyncio.create_task(_forward_client_to_daemon(client_ws, daemon_ws))
            forward_out = asyncio.create_task(_forward_daemon_to_client(daemon_ws, client_ws))
            try:
                done, pending = await asyncio.wait(
                    {forward_in, forward_out}, return_when=asyncio.FIRST_COMPLETED
                )
            finally:
                # Runs whether asyncio.wait returned normally (one side
                # finished) OR this coroutine itself was cancelled from the
                # outside (e.g. the client disconnected further up the
                # call stack) — without this in a `finally`, external
                # cancellation would leave the *other* forwarding task
                # dangling forever instead of being cleaned up. Caught by
                # a "Task was destroyed but it is pending!" warning during
                # this phase's own test run, not by inspection.
                for task in (forward_in, forward_out):
                    if not task.done():
                        task.cancel()
                for task in (forward_in, forward_out):
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
    except Exception as exc:
        logger.warning("console proxy to daemon %s failed: %s", upstream_url, exc)
        try:
            await client_ws.close(code=ws_status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


async def _forward_client_to_daemon(client_ws, daemon_ws) -> None:
    try:
        while True:
            data = await client_ws.receive_bytes()
            await daemon_ws.send(data)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


async def _forward_daemon_to_client(daemon_ws, client_ws) -> None:
    try:
        async for message in daemon_ws:
            payload = message if isinstance(message, bytes) else message.encode()
            await client_ws.send_bytes(payload)
    except Exception:
        pass
