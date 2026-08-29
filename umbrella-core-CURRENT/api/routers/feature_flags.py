"""
api/routers/feature_flags.py — REST endpoints for feature-flag management.

GET    /api/v1/feature-flags          list all flags (admin auth)
GET    /api/v1/feature-flags/{name}   get one flag by name
POST   /api/v1/feature-flags          create or update a flag (upsert)
DELETE /api/v1/feature-flags/{name}   delete a flag

All endpoints require at minimum admin-key or session auth. List/get
additionally require feature_flags.view; POST and DELETE require
feature_flags.manage. The admin key (X-Admin-Key) bypasses role-based
permission checks entirely — same pattern as every other router.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import json

from database import get_db
from api.dependencies.permissions import require_permission
from models import User
from models.audit_log import AuditLog
import services.feature_flag_service as svc

router = APIRouter(prefix="/api/v1/feature-flags", tags=["feature-flags"])


class FeatureFlagResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    description: str


class FeatureFlagUpsert(BaseModel):
    name: str
    enabled: bool
    description: str = ""


def _to_response(flag) -> FeatureFlagResponse:
    return FeatureFlagResponse(
        id=flag.id,
        name=flag.name,
        enabled=flag.enabled,
        description=flag.description,
    )


@router.get("", response_model=list[FeatureFlagResponse])
async def list_flags(
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("feature_flags.view")),
) -> list[FeatureFlagResponse]:
    """Return all feature flags, ordered by name."""
    flags = await svc.list_flags(db)
    return [_to_response(f) for f in flags]


@router.get("/{name}", response_model=FeatureFlagResponse)
async def get_flag(
    name: str,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("feature_flags.view")),
) -> FeatureFlagResponse:
    """Return a single feature flag by name."""
    from sqlalchemy import select
    from models.feature_flag import FeatureFlag

    flag = await db.scalar(select(FeatureFlag).where(FeatureFlag.name == name))
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Feature flag '{name}' not found")
    return _to_response(flag)


@router.post("", response_model=FeatureFlagResponse, status_code=200)
async def upsert_flag(
    body: FeatureFlagUpsert,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("feature_flags.manage")),
) -> FeatureFlagResponse:
    """Create or update a feature flag (upsert by name).

    FIX (FINDING-019): now writes an AuditLog row so there is a trail of
    who toggled each flag and when.
    """
    flag = await svc.set_flag(db, body.name, body.enabled, body.description)
    actor = auth.username if isinstance(auth, User) else "admin"
    db.add(AuditLog(
        actor=actor,
        actor_type="staff" if isinstance(auth, User) else "admin",
        action="feature_flag.upsert",
        target=body.name,
        details_json=json.dumps({"enabled": body.enabled, "description": body.description}),
    ))
    await db.flush()
    return _to_response(flag)


@router.delete("/{name}", response_model=dict)
async def delete_flag(
    name: str,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("feature_flags.manage")),
) -> dict:
    """Delete a feature flag by name. Returns 404 if not found.

    FIX (FINDING-019): now writes an AuditLog row on delete.
    """
    existed = await svc.delete_flag(db, name)
    if not existed:
        raise HTTPException(status_code=404, detail=f"Feature flag '{name}' not found")
    actor = auth.username if isinstance(auth, User) else "admin"
    db.add(AuditLog(
        actor=actor,
        actor_type="staff" if isinstance(auth, User) else "admin",
        action="feature_flag.delete",
        target=name,
        details_json="{}",
    ))
    await db.flush()
    return {"deleted": True}
