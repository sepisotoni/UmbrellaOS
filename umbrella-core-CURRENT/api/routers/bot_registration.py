"""
api/routers/bot_registration.py — Bot webhook registration endpoint.

The Discord bot POSTs its callback URL here on startup. Core stores it
(upsert on id=1) so bot_push_service can send events to the bot without
configuration on the core side. The URL is expected to be the bot's public
HeavenCloud address, e.g. http://<ip>:8080/webhook.

Auth: require_admin_hmac_or_session (Phase 16B Task A) — only the bot
(which has the shared secret) or a dashboard session can register.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import require_admin_hmac_or_session
from database import get_db
from models.bot_registration import BotRegistration
import services.bot_push_service as bot_push_service

router = APIRouter(prefix="/api/v1/bot", tags=["bot"])


class BotRegisterRequest(BaseModel):
    callback_url: str


class BotRegisterResponse(BaseModel):
    registered: bool
    callback_url: str


@router.post("/register", response_model=BotRegisterResponse)
async def register_bot(
    body: BotRegisterRequest,
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> BotRegisterResponse:
    """
    Upsert the bot's webhook callback URL. Always writes to id=1 so there
    is at most one registration. Subsequent bot restarts overwrite the URL
    with the (potentially new) HeavenCloud address.
    """
    if not body.callback_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="callback_url must be an http(s) URL")

    existing = await db.get(BotRegistration, 1)
    if existing:
        existing.callback_url = body.callback_url
        existing.registered_at = datetime.now(timezone.utc)
    else:
        db.add(BotRegistration(id=1, callback_url=body.callback_url))

    await db.commit()
    bot_push_service.invalidate_cache()

    return BotRegisterResponse(registered=True, callback_url=body.callback_url)
