"""
api/routers/roles.py — Role and permission endpoints.

GET /api/v1/roles             — list all roles with their permissions
GET /api/v1/roles/permissions — list all available permission keys
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services import RolesService
from services.roles_service import RoleManagementError
from api.dependencies.permissions import RoleChecker, require_owner
from models import User

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


class RolePermissionsUpdate(BaseModel):
    permissions: list[str] = Field(max_length=256)


@router.get("")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(RoleChecker(["roles.manage", "players.view"], require_all=False)),
) -> list[dict]:
    """Return all roles with their assigned permission keys."""
    return await RolesService.get_all(db)


@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(RoleChecker(["roles.manage", "players.view"], require_all=False)),
) -> list[dict]:
    """Return all available permission keys."""
    return await RolesService.get_all_permissions(db)


@router.put("/{role_id}/permissions")
async def update_role_permissions(
    role_id: str,
    body: RolePermissionsUpdate,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_owner),
) -> dict:
    """Replace a non-owner role's permission preset."""
    actor = auth.username if isinstance(auth, User) else "admin-key"
    try:
        return await RolesService.update_permissions(
            db,
            role_id,
            body.permissions,
            actor=actor,
        )
    except RoleManagementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
