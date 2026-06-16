"""
api/routers/appeals.py — Appeal endpoints.

GET  /api/v1/appeals           — list all appeals
POST /api/v1/appeals           — create a new appeal
PATCH /api/v1/appeals/{id}     — update an appeal status

All responses require admin key authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Appeal, Player, Punishment
from api.middleware.auth import require_admin_key

router = APIRouter(prefix="/api/v1/appeals", tags=["appeals"])


class AppealCreateRequest(BaseModel):
    punishment_id: str
    player_uuid: str
    message: str


class AppealUpdateRequest(BaseModel):
    status: str  # "pending", "approved", "denied", etc.


class AppealSchema(BaseModel):
    id: str
    punishment_id: str
    player_uuid: str
    status: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[AppealSchema])
async def list_appeals(
    status: str | None = Query(None, description="Filter by appeal status"),
    player_uuid: str | None = Query(None, description="Filter by player UUID"),
    skip: int = Query(0, ge=0, description="Number of appeals to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of appeals to return"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[AppealSchema]:
    """List all appeals with optional filtering by status or player."""
    query = select(Appeal)

    if status:
        query = query.where(Appeal.status == status)

    if player_uuid:
        query = query.where(Appeal.player_uuid == player_uuid)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    appeals = result.scalars().all()

    return [AppealSchema.model_validate(a) for a in appeals]


@router.post("", response_model=AppealSchema, status_code=201)
async def create_appeal(
    body: AppealCreateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> AppealSchema:
    """Create a new appeal for a punishment."""
    # Verify player exists
    player_result = await db.execute(
        select(Player).where(Player.uuid == body.player_uuid)
    )
    player = player_result.scalar_one_or_none()

    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{body.player_uuid}' not found")

    # Verify punishment exists and belongs to player
    punishment_result = await db.execute(
        select(Punishment).where(Punishment.id == body.punishment_id)
    )
    punishment = punishment_result.scalar_one_or_none()

    if punishment is None:
        raise HTTPException(status_code=404, detail=f"Punishment '{body.punishment_id}' not found")

    if punishment.player_uuid != body.player_uuid:
        raise HTTPException(
            status_code=400, detail="Punishment does not belong to the specified player"
        )

    # Create appeal
    appeal = Appeal(
        punishment_id=body.punishment_id,
        player_uuid=body.player_uuid,
        status="pending",
        message=body.message,
    )

    db.add(appeal)
    await db.flush()

    return AppealSchema.model_validate(appeal)


@router.patch("/{appeal_id}", response_model=AppealSchema)
async def update_appeal(
    appeal_id: str,
    body: AppealUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> AppealSchema:
    """Update an appeal status."""
    result = await db.execute(
        select(Appeal).where(Appeal.id == appeal_id)
    )
    appeal = result.scalar_one_or_none()

    if appeal is None:
        raise HTTPException(status_code=404, detail=f"Appeal '{appeal_id}' not found")

    appeal.status = body.status
    await db.flush()

    return AppealSchema.model_validate(appeal)
