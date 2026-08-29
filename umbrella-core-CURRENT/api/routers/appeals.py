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
from api.middleware.auth import require_plugin_key

router = APIRouter(prefix="/api/v1/appeals", tags=["appeals"])

# Valid close actions
VALID_CLOSE_ACTIONS = {
    "ACCEPT",
    "REDUCE_SENTENCE",
    "REJECT",
    "ESCALATE",
    "SCHEDULE_REVIEW",
}

# AUDIT-2026-08-29 fix: ck_appeals_status (migrations 039, 042) only permits
# these *lowercase* values. close_appeal previously wrote uppercase action
# names directly as the status ("ACCEPTED", "REJECTED", ...), which never
# matched the constraint and made every close_appeal call raise an
# unhandled CheckViolationError. This maps each close action to the
# constraint-valid status it should set.
ACTION_TO_STATUS = {
    "ACCEPT": "accepted",
    "REDUCE_SENTENCE": "reduced",
    "REJECT": "rejected",
    "ESCALATE": "escalated",
    "SCHEDULE_REVIEW": "review_scheduled",
}

# Statuses accepted by PATCH /{appeal_id} — must match ck_appeals_status
# exactly (migrations 039 + 042). Kept close to (but not identical to)
# VALID_CLOSE_ACTIONS: this endpoint sets raw status values, not actions.
VALID_APPEAL_STATUSES = {
    "open",
    "accepted",
    "denied",
    "pending",
    "rejected",
    "escalated",
    "review_scheduled",
    "reduced",
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AppealCreateRequest(BaseModel):
    punishment_id: str
    player_uuid: str
    message: str


class AppealUpdateRequest(BaseModel):
    status: str  # "open", "accepted", "denied" (constrained by ck_appeals_status)


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
    # AUDIT-2026-08-29 fix: this endpoint had no auth dependency at all —
    # unlike every other endpoint in this router and contrary to the
    # module docstring ("All responses require admin key authentication").
    # Appeals are player-initiated (like player_snapshot, alt/track, and
    # anticheat/flag), so this follows the same plugin-key convention as
    # those endpoints rather than requiring a staff permission.
    _auth: str = Depends(require_plugin_key),
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
        status="open",  # Bug #9 fix: ck_appeals_status only allows open/accepted/denied; was "pending" which always violated the constraint
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

    # AUDIT-2026-08-29 fix: body.status was written straight through with no
    # validation, so any invalid value raised a raw, unhandled
    # CheckViolationError (500) from ck_appeals_status instead of a clean
    # 400. Validate against the same set the DB constraint permits.
    if body.status not in VALID_APPEAL_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be one of: {', '.join(sorted(VALID_APPEAL_STATUSES))}",
        )

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

    # AUDIT-2026-08-29 fix: previously there was no guard against closing an
    # already-closed appeal — a closed appeal could be re-accepted,
    # re-rejected, or re-escalated indefinitely, silently re-mutating the
    # linked punishment and overwriting the audit trail (case_summary,
    # handled_by, closed_at) each time.
    if appeal.closed_at is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Appeal '{appeal_id}' is already closed (action: {appeal.action_taken}, closed at {appeal.closed_at.isoformat()})",
        )

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
    # require_permission returns either a User ORM object (session auth) or
    # a raw string (admin key hash) when the admin key is used directly.
    # SEC-2 fix: never store the raw key hash in handled_by — it leaks the
    # credential to anyone with appeals.view. Use the User's username when
    # available; fall back to the generic label "admin-key" for key-auth callers.
    if isinstance(_auth, str):
        staff_username = "admin-key"
    elif _auth and hasattr(_auth, "username"):
        staff_username = _auth.username or "unknown-user"
    else:
        staff_username = "system"

    # Execute the action
    now = datetime.now(tz=timezone.utc)

    # AUDIT-2026-08-29 fix: appeal.status was previously set to the raw
    # uppercase action name (e.g. "ACCEPTED", "REDUCED"), but
    # ck_appeals_status only permits specific lowercase values — and
    # "REDUCED" wasn't in the constraint's allowed set at all (see
    # migration 042). Every close_appeal call raised an unhandled
    # CheckViolationError at commit. ACTION_TO_STATUS maps each action to
    # its constraint-valid status; action_taken (below) still records the
    # original uppercase action name for the UI/audit log.
    if action == "ACCEPT":
        if punishment:
            punishment.active = False
            punishment.status = "PARDONED"

    elif action == "REDUCE_SENTENCE":
        if punishment:
            punishment.expires_at = body.new_expiry

    elif action in ("REJECT", "ESCALATE", "SCHEDULE_REVIEW"):
        pass  # status set uniformly below

    appeal.status = ACTION_TO_STATUS[action]

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
