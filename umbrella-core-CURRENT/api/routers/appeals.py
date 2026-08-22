"""
api/routers/appeals.py — Appeal endpoints.

GET  /api/v1/appeals             — list all appeals
POST /api/v1/appeals             — create a new appeal
PATCH /api/v1/appeals/{id}       — update an appeal status
POST /api/v1/appeals/{id}/close  — close an appeal with an action (P15 Task 3)

All responses require admin key authentication.
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from models import Appeal, Player, Punishment, AuditLog
from api.dependencies.permissions import require_permission

router = APIRouter(prefix="/api/v1/appeals", tags=["appeals"])

# Valid close actions
VALID_CLOSE_ACTIONS = {
    "ACCEPT",
    "REDUCE_SENTENCE",
    "REJECT",
    "ESCALATE",
    "SCHEDULE_REVIEW",
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AppealCreateRequest(BaseModel):
    punishment_id: str
    player_uuid: str
    message: str


class AppealUpdateRequest(BaseModel):
    status: str  # "pending", "approved", "denied", etc.


class AppealCloseRequest(BaseModel):
    action: str           # ACCEPT | REDUCE_SENTENCE | REJECT | ESCALATE | SCHEDULE_REVIEW
    staff_note: str | None = None
    new_expiry: datetime | None = None  # required when action == REDUCE_SENTENCE


class AppealSchema(BaseModel):
    id: str
    punishment_id: str
    player_uuid: str
    status: str
    message: str
    created_at: datetime
    action_taken: str | None = None
    handled_by: str | None = None
    case_summary: str | None = None
    closed_at: datetime | None = None
    ai_review_status: str | None = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AppealSchema])
async def list_appeals(
    status: str | None = Query(None, description="Filter by appeal status"),
    player_uuid: str | None = Query(None, description="Filter by player UUID"),
    skip: int = Query(0, ge=0, description="Number of appeals to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of appeals to return"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("appeals.view")),
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
    _auth: str = Depends(require_permission("appeals.manage")),
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


@router.post("/{appeal_id}/close", response_model=AppealSchema)
async def close_appeal(
    appeal_id: str,
    body: AppealCloseRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("appeals.manage")),
) -> AppealSchema:
    """
    Close an appeal with a staff decision.

    Actions:
      ACCEPT           — pardons the linked punishment (active=False, status=PARDONED)
      REDUCE_SENTENCE  — updates punishment.expires_at to new_expiry (required)
      REJECT           — sets appeal status to REJECTED
      ESCALATE         — sets appeal status to ESCALATED
      SCHEDULE_REVIEW  — sets appeal status to REVIEW_SCHEDULED

    Auto-generates a case summary and writes to the audit log.
    """
    # Validate action
    action = body.action.upper()
    if action not in VALID_CLOSE_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{action}'. Must be one of: {', '.join(sorted(VALID_CLOSE_ACTIONS))}",
        )

    # REDUCE_SENTENCE requires new_expiry
    if action == "REDUCE_SENTENCE" and body.new_expiry is None:
        raise HTTPException(
            status_code=400,
            detail="new_expiry is required when action is REDUCE_SENTENCE",
        )

    # Fetch appeal
    appeal_result = await db.execute(
        select(Appeal).where(Appeal.id == appeal_id)
    )
    appeal = appeal_result.scalar_one_or_none()
    if appeal is None:
        raise HTTPException(status_code=404, detail=f"Appeal '{appeal_id}' not found")

    # Fetch linked punishment and player for summary
    punishment_result = await db.execute(
        select(Punishment).where(Punishment.id == appeal.punishment_id)
    )
    punishment = punishment_result.scalar_one_or_none()

    player_result = await db.execute(
        select(Player).where(Player.uuid == appeal.player_uuid)
    )
    player = player_result.scalar_one_or_none()

    username = player.username if player else appeal.player_uuid
    punishment_type = punishment.type if punishment else "unknown"
    punishment_reason = punishment.reason if punishment else "unknown"

    # Determine the staff username from auth context.
    # require_permission returns the actor identifier (username or key id).
    staff_username = str(_auth) if _auth else "system"

    # Execute the action
    now = datetime.now(tz=timezone.utc)

    if action == "ACCEPT":
        if punishment:
            punishment.active = False
            punishment.status = "PARDONED"
        appeal.status = "ACCEPTED"

    elif action == "REDUCE_SENTENCE":
        if punishment:
            punishment.expires_at = body.new_expiry
        appeal.status = "REDUCED"

    elif action == "REJECT":
        appeal.status = "REJECTED"

    elif action == "ESCALATE":
        appeal.status = "ESCALATED"

    elif action == "SCHEDULE_REVIEW":
        appeal.status = "REVIEW_SCHEDULED"

    # Build case summary
    date_str = now.strftime("%Y-%m-%d")
    case_summary = (
        f"Appeal #{appeal_id} — Closed [{date_str}]\n"
        f"Player: {username} | Punishment: {punishment_type} ({punishment_reason})\n"
        f"Action Taken: {action}\n"
        f"Handled by: {staff_username}\n"
        f"Notes: {body.staff_note or 'None'}"
    )

    # Save close fields to appeal
    appeal.action_taken = action
    appeal.handled_by = staff_username
    appeal.case_summary = case_summary
    appeal.closed_at = now

    # Audit log
    audit_details = json.dumps({
        "appeal_id": appeal_id,
        "action": action,
        "punishment_id": appeal.punishment_id,
        "player_uuid": appeal.player_uuid,
        "staff_note": body.staff_note,
        "new_expiry": body.new_expiry.isoformat() if body.new_expiry else None,
    })
    audit = AuditLog(
        actor=staff_username,
        actor_type="staff",
        action="appeal.closed",
        target=appeal_id,
        details_json=audit_details,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(appeal)

    return AppealSchema.model_validate(appeal)
