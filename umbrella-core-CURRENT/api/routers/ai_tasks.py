"""
api/routers/ai_tasks.py — AI moderation task endpoints.

POST /api/v1/ai/review/player/{uuid}     — trigger AI review for a player
POST /api/v1/ai/review/appeal/{appeal_id} — trigger AI review for an appeal
GET  /api/v1/ai/tasks                    — list AI tasks
GET  /api/v1/ai/tasks/{task_id}          — single AI task detail
POST /api/v1/ai/tasks/{task_id}/approve  — staff approves AI recommendation
POST /api/v1/ai/tasks/{task_id}/deny     — staff denies AI recommendation

P15 Tasks 4 & 5:
  - /review/player and /review/appeal now return 503 on AI failure
    (not 400) with the error message, so the dashboard can show a
    "Re-review" button and staff can still proceed manually.
  - Response includes full ai_result blob from ai_service for the
    rich decision UI.
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from api.middleware.auth import require_admin_key
from api.dependencies.permissions import require_permission
from services import ai_service
from models import AITask, Appeal, AuditLog

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ApproveTaskRequest(BaseModel):
    action_taken: str
    reviewed_by: str


class DenyTaskRequest(BaseModel):
    reviewed_by: str
    reason: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_to_dict(task: AITask, include_evidence: bool = False) -> dict:
    """Serialize an AITask to a response dict."""
    d = {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "player_uuid": task.player_uuid,
        "created_at": task.created_at.isoformat(),
        "expires_at": task.expires_at.isoformat(),
        "ai_summary": task.ai_summary,
        "ai_recommendation": task.ai_recommendation,
        "ai_confidence": task.ai_confidence,
        "reviewed_by": task.reviewed_by,
        "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
        "action_taken": task.action_taken,
    }
    if include_evidence:
        # Decode evidence JSON for richer UI
        raw = task.evidence or "{}"
        try:
            evidence_obj = json.loads(raw)
        except json.JSONDecodeError:
            evidence_obj = {"raw": raw}
        d["evidence"] = evidence_obj
        # Surface top-level ai_result if present
        if "ai_result" in evidence_obj:
            d["ai_result"] = evidence_obj["ai_result"]
    return d


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/review/player/{uuid}", status_code=201)
async def trigger_player_review(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Trigger AI review of a flagged player.
    Uses GrimAC history (last 30 days) + punishment history for context.
    Returns 503 on AI failure so the dashboard can show a Re-review button.
    """
    try:
        task = await ai_service.review_flagged_player(uuid, db)
    except ai_service.AIServiceError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_review_failed", "message": str(e)},
        )

    return _task_to_dict(task, include_evidence=True)


@router.post("/review/appeal/{appeal_id}", status_code=201)
async def trigger_appeal_review(
    appeal_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Trigger AI review of an appeal.
    Pulls full context: punishment history, GrimAC ±72hr, previous appeals.
    Sets appeal.ai_review_status = COMPLETED | FAILED.
    Returns 503 on AI failure so the dashboard can show a Re-review button.
    """
    try:
        task = await ai_service.review_appeal(appeal_id, db)
    except ai_service.AIServiceError as e:
        # ai_service already set ai_review_status=FAILED and committed
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_review_failed", "message": str(e)},
        )

    # Also return the appeal's ai_review_result for the dashboard
    appeal = await db.scalar(
        select(Appeal).where(Appeal.id == appeal_id)
    )
    ai_result = None
    if appeal and appeal.ai_review_result:
        try:
            ai_result = json.loads(appeal.ai_review_result)
        except json.JSONDecodeError:
            ai_result = None

    response = _task_to_dict(task, include_evidence=True)
    response["ai_review_status"] = getattr(appeal, "ai_review_status", None) if appeal else None
    response["ai_result"] = ai_result
    return response


@router.get("/tasks")
async def list_ai_tasks(
    status: str | None = None,
    task_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("punishments.view")),
):
    """List all AI tasks with filters: status, task_type. Pagination: skip, limit."""
    query = select(AITask)

    if status:
        query = query.where(AITask.status == status)
    if task_type:
        query = query.where(AITask.task_type == task_type)

    query = query.order_by(AITask.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [_task_to_dict(t) for t in tasks]


@router.get("/tasks/{task_id}")
async def get_ai_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("punishments.view")),
):
    """Get single AI task with full evidence."""
    task = await db.scalar(select(AITask).where(AITask.id == task_id))
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")

    return _task_to_dict(task, include_evidence=True)


@router.post("/tasks/{task_id}/approve")
async def approve_ai_task(
    task_id: int,
    body: ApproveTaskRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("punishments.create")),
):
    """
    Staff approves AI recommendation.
    Sets status=approved, records reviewer.
    Creates audit log: ai_task.approved.
    """
    task = await db.scalar(select(AITask).where(AITask.id == task_id))
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")

    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Task is not pending")

    task.status = "approved"
    task.reviewed_by = body.reviewed_by
    task.reviewed_at = datetime.utcnow()
    task.action_taken = body.action_taken

    audit = AuditLog(
        actor=body.reviewed_by,
        actor_type="staff",
        action="ai_task.approved",
        target=str(task_id),
        details_json=json.dumps({
            "task_id": task_id,
            "action_taken": body.action_taken,
        }),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(task)

    return _task_to_dict(task, include_evidence=True)


@router.post("/tasks/{task_id}/deny")
async def deny_ai_task(
    task_id: int,
    body: DenyTaskRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("punishments.create")),
):
    """
    Staff denies AI recommendation.
    Sets status=denied.
    Creates audit log: ai_task.denied.
    """
    task = await db.scalar(select(AITask).where(AITask.id == task_id))
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")

    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Task is not pending")

    task.status = "denied"
    task.reviewed_by = body.reviewed_by
    task.reviewed_at = datetime.utcnow()

    audit = AuditLog(
        actor=body.reviewed_by,
        actor_type="staff",
        action="ai_task.denied",
        target=str(task_id),
        details_json=json.dumps({
            "task_id": task_id,
            "reason": body.reason or "",
        }),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(task)

    return _task_to_dict(task, include_evidence=True)
