"""Staff management — promote and demote."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from api.dependencies.permissions import require_permission
from models import User
from models.permissions import Role
from services.staff_service import StaffManageError, manage_staff_role

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


class StaffManageRequest(BaseModel):
    user_id: str
    action: Literal["promote", "demote"]


class StaffManageResponse(BaseModel):
    user_id: str
    username: str
    previous_role: str
    new_role: str
    action: str


@router.post("/manage", response_model=StaffManageResponse)
async def staff_manage(
    body: StaffManageRequest,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("roles.manage")),
) -> StaffManageResponse:
    actor_role_name = None
    if isinstance(auth, User) and auth.role_id:
        role = await db.scalar(select(Role).where(Role.id == auth.role_id))
        actor_role_name = role.name if role else None

    try:
        result = await manage_staff_role(
            db, body.user_id, body.action, actor_role_name=actor_role_name,
        )
        return StaffManageResponse(**result)
    except StaffManageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
