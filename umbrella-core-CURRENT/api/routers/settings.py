"""
api/routers/settings.py — Settings registry endpoints (owner only).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from services import SettingsService
from api.dependencies.permissions import require_owner
from api.middleware.auth import require_admin_hmac_or_session
from models import User

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


@router.get("")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    # GET: accept PBKDF2 MAC (bot) or dashboard session in addition to raw admin key
    auth: str = Depends(require_admin_hmac_or_session),
) -> list[dict]:
    """Return all settings. Bot callers (PBKDF2 MAC) and admin-key callers get
    unmasked values; dashboard session callers get sensitive values masked."""
    unmasked = isinstance(auth, str)
    return await SettingsService.get_all(db, unmasked=unmasked)


@router.get("/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    # GET: accept PBKDF2 MAC (bot) or dashboard session in addition to raw admin key
    auth: str = Depends(require_admin_hmac_or_session),
) -> dict:
    # PBKDF2 / admin-key callers (bot, plugin) get the real value; dashboard users get masked
    unmasked = isinstance(auth, str)
    setting = await SettingsService.get_by_key(db, key, unmasked=unmasked)
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    if not unmasked and setting.get("sensitive"):
        setting = {**setting, "value": "***"}
    return setting


@router.post("/{key}")
async def create_or_update_setting(
    key: str,
    body: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_owner),
) -> dict:
    """Create a new setting or update an existing one.

    Identical to PATCH but upserts — used when a template key may not
    yet exist (e.g. during initial seeding from external tools or tests).
    """
    actor = auth.username if isinstance(auth, User) else "dashboard"
    if body.value == "***":
        raise HTTPException(status_code=400, detail="Cannot save masked secret placeholder")
    from models.setting import Setting
    from sqlalchemy import select
    existing = await db.scalar(select(Setting).where(Setting.key == key))
    if existing is None:
        # Derive category from the key prefix (e.g. "verification.dm_prompt" -> "verification")
        category = key.split(".")[0] if "." in key else "general"
        new_setting = Setting(
            key=key,
            value=body.value,
            category=category,
            description=f"Auto-created: {key}",
            sensitive=False,
            requires_restart=False,
        )
        db.add(new_setting)
        await db.commit()
        await db.refresh(new_setting)
        from services import SettingsService
        return SettingsService._to_dict(new_setting, unmasked=False)
    updated = await SettingsService.update(
        db=db, key=key, new_value=body.value, actor=actor, actor_type="staff",
    )
    return updated


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
