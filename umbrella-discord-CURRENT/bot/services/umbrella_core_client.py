"""
bot/services/umbrella_core_client.py — umbrella-discord's HTTP client into
umbrella-core, over the Capability Registry's REST adapter
(POST /api/v1/capabilities/{name}/invoke).

This is the ONLY place in umbrella-discord that talks to umbrella-core
directly - cogs call through this client rather than constructing URLs/
requests themselves, mirroring the exact same "one implementation"
principle services/daemon_client.py already established on the core side
for talking to umbrella-daemon. Every cog is a thin caller into this, per
the Phase 6 roadmap requirement - no cog constructs its own AI/moderation/
investigation logic in-process, unlike Moo-assistant's monolithic bot.py,
where umbrella-core and umbrella-discord were one process sharing Python
objects directly. They are two separate deployable services here, so this
client is the actual integration boundary, not an implementation detail.

Auth (Phase 16B Task A): requests are authenticated with a PBKDF2-HMAC-SHA256
MAC derived from the shared secret. The raw key is never sent on the wire.
Two headers replace X-Admin-Key:
  X-Auth-MAC       — hex-encoded 32-byte PBKDF2 output
  X-Auth-Timestamp — Unix timestamp (int, seconds UTC)

Core verifies by re-deriving the MAC with the same KDF and comparing with
hmac.compare_digest(). Requests older than 30 seconds are rejected to
prevent replay attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from typing import Any

import httpx


class UmbrellaCoreError(Exception):
    """Raised for any failure calling umbrella-core - a capability
    returning an error response, a network failure, or an unexpected
    response shape. Cogs catch this one exception type to turn a failure
    into a user-facing Discord message, rather than needing to know every
    possible underlying cause."""

    def __init__(
        self, message: str, *, status_code: int | None = None, code: str | None = None
    ):
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class UmbrellaCoreClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    def _make_auth_headers(
        self,
        method: str,
        target: str,
        body: bytes = b"",
    ) -> dict[str, str]:
        """Create a request-bound v2 MAC.

        The signature covers method, exact path/query, body hash, timestamp
        and a random nonce, so a captured credential cannot be replayed for
        another endpoint or payload.
        """
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        body_hash = hashlib.sha256(body).hexdigest()
        canonical = (
            f"{method.upper()}\n{target}\n{timestamp}\n{nonce}\n{body_hash}"
        ).encode("utf-8")
        mac = hmac.new(
            self._api_key.encode("utf-8"), canonical, hashlib.sha256
        ).hexdigest()
        return {
            "X-Auth-Version": "2",
            "X-Auth-MAC": mac,
            "X-Auth-Timestamp": timestamp,
            "X-Auth-Nonce": nonce,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        discord_user_id: str | None = None,
    ) -> httpx.Response:
        target = path
        if params:
            query = str(httpx.QueryParams(params))
            if query:
                target += ("&" if "?" in target else "?") + query

        body = (
            json.dumps(
                json_body,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
            if json_body is not None
            else b""
        )
        headers = self._make_auth_headers(method, target, body)
        headers["Accept"] = "application/json"
        if body:
            headers["Content-Type"] = "application/json"
        if discord_user_id is not None:
            headers["X-Discord-User-Id"] = discord_user_id

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as http:
                return await http.request(
                    method,
                    f"{self._base_url}{target}",
                    headers=headers,
                    content=body if body else None,
                )
        except httpx.RequestError as exc:
            raise UmbrellaCoreError(
                f"Could not reach umbrella-core: {exc}"
            ) from exc

    @staticmethod
    def _parse_error(response: httpx.Response) -> tuple[str, str | None]:
        """Parse an error response body into (message, code).

        FastAPI wraps HTTPException as {"detail": "..."} but some older
        endpoints and custom error handlers use {"error": "...", "code": "..."}.
        Check both so callers always get a useful message regardless of which
        shape the server returned. Falls back to raw response text when the
        body is not JSON or neither key is present.
        """
        try:
            body = response.json()
            message = body.get("detail") or body.get("error") or response.text
            code = body.get("code")
        except ValueError:
            message = response.text
            code = None
        return message, code

    async def invoke(
        self,
        capability_name: str,
        params: dict[str, Any],
        *,
        discord_user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Calls a capability by name, returning its result as a plain dict.
        Raises UmbrellaCoreError on any non-2xx response or network
        failure - the caller doesn't need to distinguish "permission
        denied" from "validation error" from "capability not found"
        structurally; status_code/code are attached for callers that want
        to branch on them (e.g. a cog showing a friendlier message for a
        403 than a 500).

        `discord_user_id`, when given, sends the invoking Discord user's
        snowflake as X-Discord-User-Id - closes Phase 6's slash-command ->
        REST-permission mapping gap (see registry/context.py's
        `from_discord_user` and registry/adapters/rest.py's own docstring
        on umbrella-core). This only does anything if this client's own
        API key was itself granted `identity.discord_delegate` - without
        that, umbrella-core ignores the header and falls back to the
        key's own blanket scope, exactly like every call before this
        parameter existed. Every cog passes `str(interaction.user.id)`
        here; omitting it (the default) preserves the pre-Phase-6 behavior
        exactly, so this is purely additive.
        """
        response = await self._request(
            "POST",
            f"/api/v1/capabilities/{capability_name}/invoke",
            json_body=params,
            discord_user_id=discord_user_id,
        )

        if response.status_code >= 400:
            message, code = UmbrellaCoreClient._parse_error(response)
            raise UmbrellaCoreError(
                message, status_code=response.status_code, code=code
            )

        try:
            return response.json()
        except ValueError as exc:
            raise UmbrellaCoreError(
                f"umbrella-core returned a non-JSON response: {exc}"
            ) from exc

    async def list_capabilities(self) -> list[dict[str, Any]]:
        """Lists every capability this API key is permitted to see -
        useful for a cog building help text or validating a capability
        name exists before invoking it."""
        response = await self._request("GET", "/api/v1/capabilities")

        if response.status_code >= 400:
            raise UmbrellaCoreError(
                f"umbrella-core returned {response.status_code}",
                status_code=response.status_code,
            )

        return response.json()

    async def register_bot(self, callback_url: str) -> None:
        """Register this bot's webhook URL with umbrella-core so it can
        receive push events (Phase 16B Task B). Called once on startup."""
        response = await self._request(
            "POST",
            "/api/v1/bot/register",
            json_body={"callback_url": callback_url},
        )

        if response.status_code >= 400:
            raise UmbrellaCoreError(
                f"Bot registration failed: {response.status_code}",
                status_code=response.status_code,
            )

    async def push_command_manifest(self, commands: list[dict]) -> None:
        """POST /api/v1/bot/commands — push slash command manifest to core.
        Called once on startup after tree.sync() so the dashboard can read
        real command data without hardcoding."""
        response = await self._request(
            "POST",
            "/api/v1/bot/commands",
            json_body={"commands": commands},
        )

        if response.status_code >= 400:
            raise UmbrellaCoreError(
                f"Command manifest push failed: {response.status_code}",
                status_code=response.status_code,
            )

    async def get(self, path: str) -> dict[str, Any]:
        """Makes an authenticated GET request to umbrella-core at the given
        path (e.g. '/api/v1/settings/some_key') and returns the parsed JSON
        response. Uses the same PBKDF2 auth headers as every other method.
        Raises UmbrellaCoreError on non-2xx responses or network failures."""
        response = await self._request("GET", path)

        if response.status_code >= 400:
            message, code = UmbrellaCoreClient._parse_error(response)
            raise UmbrellaCoreError(
                message, status_code=response.status_code, code=code
            )

        try:
            return response.json()
        except ValueError as exc:
            raise UmbrellaCoreError(
                f"umbrella-core returned a non-JSON response: {exc}"
            ) from exc

    async def ask_ai(self, message: str, context: str | None = None) -> dict[str, Any]:
        """POST /api/v1/ai/copilot — send a natural-language question to the
        AI copilot and return the parsed response dict (keys: response,
        model_used, latency_ms). Uses the same PBKDF2 auth headers as every
        other method. Raises UmbrellaCoreError on failure."""
        payload: dict[str, Any] = {"message": message}
        if context is not None:
            payload["context"] = context
        response = await self._request(
            "POST",
            "/api/v1/ai/copilot",
            json_body=payload,
        )

        if response.status_code >= 400:
            message, code = UmbrellaCoreClient._parse_error(response)
            raise UmbrellaCoreError(
                message, status_code=response.status_code, code=code
            )

        try:
            return response.json()
        except ValueError as exc:
            raise UmbrellaCoreError(
                f"umbrella-core returned a non-JSON response: {exc}"
            ) from exc

    async def search_knowledge(self, query: str, limit: int = 5) -> dict[str, Any]:
        """GET /api/v1/knowledge?query=<q>&limit=<n>

        Returns {"entries": [...], "total": int} — same shape the knowledge
        capability returned, so KnowledgeCog._format_result() works unchanged.
        Uses the same PBKDF2 auth headers as every other method.
        Raises UmbrellaCoreError on non-2xx or network failure.
        """
        response = await self._request(
            "GET",
            "/api/v1/knowledge",
            params={"query": query, "limit": limit},
        )

        if response.status_code >= 400:
            message, code = UmbrellaCoreClient._parse_error(response)
            raise UmbrellaCoreError(
                message, status_code=response.status_code, code=code
            )

        try:
            return response.json()
        except ValueError as exc:
            raise UmbrellaCoreError(
                f"umbrella-core returned a non-JSON response: {exc}"
            ) from exc

    async def push_guild_channels(self, channels: list[dict]) -> None:
        """POST /api/v1/bot/channels — push guild text channel list to core.
        Called on startup (and again in on_ready if guild cache was cold in
        setup_hook). Dashboard reads this to populate the broadcaster dropdown.
        """
        response = await self._request(
            "POST",
            "/api/v1/bot/channels",
            json_body={"channels": channels},
        )

        if response.status_code >= 400:
            raise UmbrellaCoreError(
                f"Guild channels push failed: {response.status_code}",
                status_code=response.status_code,
            )

    async def push_guild_roles(self, roles: list[dict]) -> None:
        """POST /api/v1/bot/roles — push mentionable guild role list to core.
        Called on startup (and again in on_ready). Dashboard reads this to
        populate the broadcaster role-mention dropdown.
        """
        response = await self._request(
            "POST",
            "/api/v1/bot/roles",
            json_body={"roles": roles},
        )

        if response.status_code >= 400:
            raise UmbrellaCoreError(
                f"Guild roles push failed: {response.status_code}",
                status_code=response.status_code,
            )
