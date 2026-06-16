"""
api/routers/settings.py — Settings registry endpoints.

GET  /api/v1/settings           — list all settings (admin)
GET  /api/v1/settings/{key}     — get a single setting (admin)
PATCH /api/v1/settings/{key}    — update a setting value (admin)

All responses mask sensitive settings unless the actor has manage_secrets.
Phase 1: auth is admin key only. Phase 3: will check manage_settings permission.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from services import SettingsService
from api.middleware.auth import require_admin_key

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


@router.get("")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[dict]:
    """Return all settings. Sensitive values are masked."""
    return await SettingsService.get_all(db)


@router.get("/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> dict:
    """Return a single setting by key."""
    setting = await SettingsService.get_by_key(db, key)
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return setting


@router.patch("/{key}")
async def update_setting(
    key: str,
    body: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> dict:
    """
    Update a setting value. Automatically writes an audit log entry.
    Phase 1: actor is hardcoded as 'dashboard'. Phase 3: use session identity.
    """
    updated = await SettingsService.update(
        db=db,
        key=key,
        new_value=body.value,
        actor="dashboard",
        actor_type="staff",
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return updated
