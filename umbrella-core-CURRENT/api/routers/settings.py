"""
api/routers/settings.py — Settings registry endpoints (owner only).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from services import SettingsService
from services.settings_service import write_env_value
from services.ai_config_service import sync_task_model_setting
from api.dependencies.permissions import require_owner, require_permission
from api.middleware.auth import require_admin_hmac_or_session
from models import User

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


def _unmask_settings(auth: str) -> bool:
    """Dashboard sessions must never see raw secrets. Admin key, HMAC, and plugin callers may."""
    return auth != "session"


@router.get("")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    # GET: accept PBKDF2 MAC (bot) or dashboard session in addition to raw admin key
    auth: str = Depends(require_admin_hmac_or_session),
    _perm=Depends(require_permission("settings.view")),
) -> list[dict]:
    """Return all settings. Bot callers (PBKDF2 MAC) and admin-key callers get
    unmasked values; dashboard session callers get sensitive values masked."""
    unmasked = _unmask_settings(auth)
    return await SettingsService.get_all(db, unmasked=unmasked)


@router.get("/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    # GET: accept PBKDF2 MAC (bot) or dashboard session in addition to raw admin key
    auth: str = Depends(require_admin_hmac_or_session),
    _perm=Depends(require_permission("settings.view")),
) -> dict:
    # PBKDF2 / admin-key callers (bot, plugin) get the real value; dashboard users get masked
    unmasked = _unmask_settings(auth)
    setting = await SettingsService.get_by_key(db, key, unmasked=unmasked)
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    # AUDIT-2026-08-30 fix: this used to unconditionally re-mask any
    # sensitive setting to "***" here, redundantly duplicating (and, once
    # SettingsService._to_dict was fixed to only mask non-empty values,
    # actively overriding/undoing) the masking decision get_by_key already
    # makes correctly. list_settings below has no equivalent duplicate
    # check and was never affected. Removed rather than fixed in parallel —
    # get_by_key's return value is already correct on its own.
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
        raise HTTPException(
            status_code=400, detail="Cannot save masked secret placeholder"
        )
    updated = await SettingsService.update(
        db=db,
        key=key,
        new_value=body.value,
        actor=actor,
        actor_type="staff",
        create_if_missing=True,
        commit=False,
    )
    if updated is None:
        # An upsert must never return an absent setting; avoid persisting
        # a model configuration with no corresponding setting row.
        raise HTTPException(status_code=500, detail="Setting upsert returned no result")
    await sync_task_model_setting(db, key, body.value)
    await db.commit()
    write_env_value(key, body.value)
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
        raise HTTPException(
            status_code=400, detail="Cannot save masked secret placeholder"
        )
    updated = await SettingsService.update(
        db=db,
        key=key,
        new_value=body.value,
        actor=actor,
        actor_type="staff",
        commit=False,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    # Save the human-facing setting, its audit row, and the effective
    # ai_model_configs row in ONE transaction. A failed model sync must not
    # leave the UI reporting a configuration that the router does not use.
    await sync_task_model_setting(db, key, body.value)
    await db.commit()
    write_env_value(key, body.value)
    return updated
