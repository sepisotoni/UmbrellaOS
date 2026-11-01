"""Versioned Discord-bot request authentication.

v2 binds the MAC to method, exact path/query, body hash, timestamp and a
single-use nonce. Legacy timestamp-only PBKDF2 verification remains accepted
temporarily for rolling upgrades, but new bot traffic uses v2.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time

from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.requests import Request

AUTH_WINDOW_SECONDS = 30
NONCE_TTL_SECONDS = 90


def _request_target(request: Request) -> str:
    target = request.url.path
    if request.url.query:
        target += "?" + request.url.query
    return target


def _canonical_v2(
    method: str,
    target: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> bytes:
    body_hash = hashlib.sha256(body).hexdigest()
    return (
        f"{method.upper()}\n{target}\n{timestamp}\n{nonce}\n{body_hash}"
    ).encode("utf-8")


async def verify_bot_mac(
    *,
    request: Request,
    mac: str | None,
    timestamp: str | None,
    version: str | None,
    nonce: str | None,
    secret: str,
    redis: Redis,
) -> None:
    if not mac or not timestamp:
        raise HTTPException(status_code=401, detail="Incomplete bot authentication")

    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid timestamp") from exc
    if abs(time.time() - ts) > AUTH_WINDOW_SECONDS:
        raise HTTPException(status_code=401, detail="Timestamp out of window")

    if version == "2":
        if (
            not nonce
            or len(nonce) < 16
            or len(nonce) > 128
            or any(ch not in "0123456789abcdefABCDEF" for ch in nonce)
        ):
            raise HTTPException(status_code=401, detail="Invalid auth nonce")

        body = await request.body()
        canonical = _canonical_v2(
            request.method,
            _request_target(request),
            timestamp,
            nonce,
            body,
        )
        expected = hmac.new(
            secret.encode("utf-8"), canonical, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, mac):
            raise HTTPException(status_code=401, detail="Invalid MAC")

        replay_key = f"bot-auth:v2:nonce:{nonce}"
        try:
            inserted = await redis.set(
                replay_key,
                "1",
                ex=NONCE_TTL_SECONDS,
                nx=True,
            )
        except RedisError as exc:
            raise HTTPException(
                status_code=503,
                detail="Bot replay protection is unavailable",
            ) from exc
        if not inserted:
            raise HTTPException(status_code=401, detail="Replayed auth nonce")
        return

    if version not in (None, "", "1"):
        raise HTTPException(status_code=401, detail="Unsupported auth version")

    # Rolling-upgrade compatibility for older bot builds.
    expected = (
        await asyncio.to_thread(
            hashlib.pbkdf2_hmac,
            "sha256",
            secret.encode(),
            str(ts).encode(),
            100_000,
            dklen=32,
        )
    ).hex()
    if not hmac.compare_digest(expected, mac):
        raise HTTPException(status_code=401, detail="Invalid MAC")
