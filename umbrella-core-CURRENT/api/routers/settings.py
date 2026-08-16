"""
api/routers/settings.py — Settings registry endpoints (owner only).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from services import SettingsService
from api.dependencies.permissions import require_owner
from models import User

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


@router.get("")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_owner),
) -> list[dict]:
    """Return all settings. Sensitive values are masked unless admin key."""
    unmasked = isinstance(auth, str)
    return await SettingsService.get_all(db, unmasked=unmasked)


@router.get("/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_owner),
) -> dict:
    # Admin-key callers (bot, plugin) get the real value; dashboard users get masked
    unmasked = isinstance(auth, str)
    setting = await SettingsService.get_by_key(db, key, unmasked=unmasked)
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    if not unmasked and setting.get("sensitive"):
        setting = {**setting, "value": "***"}
    return setting


@router.patch("/{key}")
async def update_setting(
    key: str,
    body: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_owner),
) -> dict:
    actor = auth.username if isinstance(auth, User) else "dashboard"
    if body.value == "***":
        raise HTTPException(status_code=400, detail="Cannot save masked secret placeholder")
    updated = await SettingsService.update(
        db=db, key=key, new_value=body.value, actor=actor, actor_type="staff",
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return updated
