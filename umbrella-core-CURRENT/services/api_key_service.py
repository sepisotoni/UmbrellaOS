"""
services/api_key_service.py — Scoped, revocable API keys for machine-to-
machine callers (Discord bot, CLI, external integrations).

An API key is deliberately NOT a second admin-key bootstrap tier: it can
only ever carry an explicit, finite list of permission keys, never a
superuser/wildcard grant — see `create_api_key`'s validation. If something
needs full access, it should be a session-authenticated staff account, not
an API key with every permission listed on it.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.api_key import ApiKey

API_KEY_PREFIX = "umbr_"


class ApiKeyError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "API_KEY_ERROR", status_code)


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class ApiKeyService:
    @staticmethod
    async def create_api_key(
        db: AsyncSession,
        name: str,
        permissions: list[str],
        created_by: str | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[ApiKey, str]:
        """
        Returns (ApiKey, plaintext_key). The plaintext value is returned
        exactly once, here — it is not recoverable afterward, only its hash
        is persisted. Callers (the capability layer) must surface it to the
        operator immediately and never log it.
        """
        if "*" in permissions:
            raise ApiKeyError("API keys cannot carry a wildcard permission — grant explicit keys only")

        plaintext = API_KEY_PREFIX + secrets.token_urlsafe(32)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            if expires_in_days is not None
            else None
        )

        key = ApiKey(
            name=name,
            key_hash=_hash_key(plaintext),
            key_prefix=plaintext[:12],
            permissions=permissions,
            created_by=created_by,
            expires_at=expires_at,
        )
        db.add(key)
        await db.flush()
        return key, plaintext

    @staticmethod
    async def verify_api_key(db: AsyncSession, plaintext: str) -> ApiKey:
        """
        Look up and validate an API key by its plaintext value. Raises
        ApiKeyError (401) for any invalid/revoked/expired key — deliberately
        the same error for "doesn't exist" and "revoked"/"expired" so a
        caller probing for valid key formats learns nothing extra from the
        distinction.
        """
        key_hash = _hash_key(plaintext)
        key = await db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if key is None:
            raise ApiKeyError("invalid API key", 401)
        if key.revoked:
            raise ApiKeyError("invalid API key", 401)
        if key.expires_at is not None:
            expires_at = key.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= expires_at:
                raise ApiKeyError("invalid API key", 401)

        key.last_used_at = datetime.now(timezone.utc)
        await db.flush()
        return key

    @staticmethod
    async def list_api_keys(db: AsyncSession) -> list[ApiKey]:
        result = await db.execute(select(ApiKey).order_by(ApiKey.name))
        return list(result.scalars().all())

    @staticmethod
    async def revoke_api_key(db: AsyncSession, api_key_id: str) -> ApiKey:
        key = await db.get(ApiKey, api_key_id)
        if key is None:
            raise ApiKeyError(f"no API key with id {api_key_id!r}", 404)
        key.revoked = True
        await db.flush()
        return key
