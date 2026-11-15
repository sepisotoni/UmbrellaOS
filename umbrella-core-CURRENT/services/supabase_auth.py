"""Verify Supabase Auth access tokens and resolve their signing keys."""

import asyncio
import time
from typing import Any

import httpx
import jwt
from fastapi import HTTPException

from config import get_settings

_JWKS_CACHE: dict[str, Any] = {}
_JWKS_CACHE_EXPIRES_AT = 0.0
_JWKS_LOCK = asyncio.Lock()
_JWKS_TTL_SECONDS = 300


async def _get_jwks(url: str, *, force_refresh: bool = False) -> dict[str, Any]:
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRES_AT

    if (
        not force_refresh
        and url == _JWKS_CACHE.get("_url")
        and time.monotonic() < _JWKS_CACHE_EXPIRES_AT
    ):
        return _JWKS_CACHE

    async with _JWKS_LOCK:
        if (
            not force_refresh
            and url == _JWKS_CACHE.get("_url")
            and time.monotonic() < _JWKS_CACHE_EXPIRES_AT
        ):
            return _JWKS_CACHE

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                jwks = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=503, detail="Unable to validate Supabase access token"
            ) from exc

        if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
            raise HTTPException(
                status_code=503, detail="Supabase returned an invalid signing-key set"
            )

        _JWKS_CACHE = {**jwks, "_url": url}
        _JWKS_CACHE_EXPIRES_AT = time.monotonic() + _JWKS_TTL_SECONDS
        return _JWKS_CACHE


async def validate_access_token(token: str) -> dict[str, Any]:
    """Validate issuer, audience, signature, expiry, and required app claims."""
    supabase_url = get_settings().supabase_url.rstrip("/")
    if not supabase_url:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc

    algorithm = header.get("alg")
    key_id = header.get("kid")
    if algorithm not in {"ES256", "RS256"} or not isinstance(key_id, str):
        raise HTTPException(status_code=401, detail="Unsupported access token")

    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    jwks = await _get_jwks(jwks_url)
    jwk_data = next(
        (
            key
            for key in jwks["keys"]
            if isinstance(key, dict) and key.get("kid") == key_id
        ),
        None,
    )
    if jwk_data is None:
        jwks = await _get_jwks(jwks_url, force_refresh=True)
        jwk_data = next(
            (
                key
                for key in jwks["keys"]
                if isinstance(key, dict) and key.get("kid") == key_id
            ),
            None,
        )
        if jwk_data is None:
            raise HTTPException(
                status_code=401, detail="Unknown access-token signing key"
            )

    try:
        signing_key = jwt.PyJWK.from_dict(jwk_data, algorithm=algorithm).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=f"{supabase_url}/auth/v1",
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc

    app_metadata = claims.get("app_metadata")
    if not isinstance(app_metadata, dict):
        raise HTTPException(status_code=403, detail="Supabase authorization claims missing")

    user_id = app_metadata.get("umbrella_user_id")
    authz_version = app_metadata.get("umbrella_authz_version")
    permissions = app_metadata.get("umbrella_permissions")
    if (
        not isinstance(user_id, str)
        or not isinstance(authz_version, int)
        or not isinstance(permissions, list)
        or any(not isinstance(permission, str) for permission in permissions)
    ):
        raise HTTPException(status_code=403, detail="Supabase authorization claims invalid")

    return claims

