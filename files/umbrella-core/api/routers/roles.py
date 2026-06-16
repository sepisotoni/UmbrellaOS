"""
api/routers/roles.py — Role and permission endpoints.

GET /api/v1/roles             — list all roles with their permissions
GET /api/v1/roles/permissions — list all available permission keys
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services import RolesService
from api.middleware.auth import require_admin_key

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[dict]:
    """Return all roles with their assigned permission keys."""
    return await RolesService.get_all(db)


@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[dict]:
    """Return all available permission keys."""
    return await RolesService.get_all_permissions(db)
