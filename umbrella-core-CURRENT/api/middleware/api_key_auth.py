"""
api/middleware/api_key_auth.py — Adds API-key authentication as a third
option alongside the existing admin-key/session tiers, for the Capability
Registry's REST adapter specifically (machine-to-machine callers — the
Discord bot, CLI, external integrations — are the intended users of API
keys; see services/api_key_service.py for why a key can never carry
superuser/wildcard access).
"""
import hashlib
import hmac
import time

from fastapi import Depends, Header, Security
from fastapi.exceptions import HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from api.middleware.session import admin_key_header, require_admin_key_or_session
from config import settings
from database import get_db
from models import User
from models.api_key import ApiKey
from services.api_key_service import ApiKeyService
import services.threat_detection_service as threat_detection_service


async def require_capability_auth(
    request: Request,
    x_api_key: str | None = Header(default=None),
    x_admin_key: str | None = Security(admin_key_header),
    x_auth_mac: str | None = Header(default=None),
    x_auth_timestamp: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | str | ApiKey:
    """
    If an `X-Api-Key` header is present, authenticate via it exclusively —
    a request presenting an API key is never also evaluated against
    session/admin-key auth, and a missing/invalid session token never masks
    a valid API key (or vice versa).

    Deliberately calls `require_admin_key_or_session` as a plain function
    here, NOT via FastAPI's `Depends()` — declaring it as a dependency
    would make FastAPI resolve it eagerly for every request (including ones
    presenting a perfectly valid API key), and it raises a 401 on its own
    when neither an admin key nor a session token is present. Since a
    request authenticating via API key legitimately has neither, that
    eager evaluation would incorrectly reject valid API-key requests before
    this function's own logic ever ran. Calling it manually, only in the
    branch where it's actually needed, is what avoids that.

    Phase 9 addition: any 401 from either path is recorded as an
    `auth_failure` security event (client IP only — never the credential
    itself, matching this codebase's existing convention of hashing rather
    than logging API keys) before re-raising, feeding threat detection's
    brute-force/credential-stuffing alerting without changing the auth
    outcome itself.
    """
    client_ip = request.client.host if request.client else None
    try:
        # PBKDF2 MAC from the Discord bot (Phase 16B) — checked first so the
        # bot never needs an API key or session token to call capabilities.
        if x_auth_mac and x_auth_timestamp:
            try:
                ts = int(x_auth_timestamp)
            except ValueError:
                raise HTTPException(status_code=401, detail="Invalid timestamp")
            if abs(time.time() - ts) > 30:
                raise HTTPException(status_code=401, detail="Timestamp out of window")
            expected = hashlib.pbkdf2_hmac(
                "sha256",
                settings.admin_key.encode(),
                str(ts).encode(),
                100_000,
                dklen=32,
            ).hex()
            if not hmac.compare_digest(expected, x_auth_mac):
                raise HTTPException(status_code=401, detail="Invalid MAC")
            return "hmac"
        if x_api_key is not None:
            return await ApiKeyService.verify_api_key(db, x_api_key)
        return await require_admin_key_or_session(x_admin_key, authorization, db)
    except (HTTPException, AppException) as exc:
        if exc.status_code == 401:
            await threat_detection_service.record(event_type="auth_failure", source_ip=client_ip)
        raise

