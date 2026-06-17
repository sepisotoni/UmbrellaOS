"""
api/routers/ai_tasks.py — AI moderation task endpoints.

POST /api/v1/ai/review/player/{uuid}
POST /api/v1/ai/review/appeal/{appeal_id}
GET  /api/v1/ai/tasks
GET  /api/v1/ai/tasks/{task_id}
POST /api/v1/ai/tasks/{task_id}/approve
POST /api/v1/ai/tasks/{task_id}/deny
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from api.middleware.auth import require_admin_key
from services import ai_service
from models import AITask, AuditLog

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ApproveTaskRequest(BaseModel):
    action_taken: str
    reviewed_by: str


class DenyTaskRequest(BaseModel):
    reviewed_by: str
    reason: str | None = None


@router.post("/review/player/{uuid}", status_code=201)
async def trigger_player_review(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Trigger AI review of a flagged player.
    Calls ai_service.review_flagged_player().
    Returns created AITask.
    """
    try:
        task = await ai_service.review_flagged_player(uuid, db)
    except ai_service.AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "player_uuid": task.player_uuid,
        "created_at": task.created_at.isoformat(),
        "expires_at": task.expires_at.isoformat(),
        "ai_summary": task.ai_summary,
        "ai_recommendation": task.ai_recommendation,
        "ai_confidence": task.ai_confidence,
        "evidence": task.evidence,
        "reviewed_by": task.reviewed_by,
        "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
        "action_taken": task.action_taken,
    }


@router.post("/review/appeal/{appeal_id}", status_code=201)
async def trigger_appeal_review(
    appeal_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Trigger AI review of an appeal.
    Calls ai_service.review_appeal().
    Returns created AITask.
    """
    try:
        task = await ai_service.review_appeal(appeal_id, db)
    except ai_service.AIServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "player_uuid": task.player_uuid,
        "created_at": task.created_at.isoformat(),
        "expires_at": task.expires_at.isoformat(),
        "ai_summary": task.ai_summary,
        "ai_recommendation": task.ai_recommendation,
        "ai_confidence": task.ai_confidence,
        "evidence": task.evidence,
        "reviewed_by": task.reviewed_by,
        "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
        "action_taken": task.action_taken,
    }


@router.get("/tasks")
async def list_ai_tasks(
    status: str | None = None,
    task_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    List all AI tasks with filters: status, task_type.
    Pagination: skip, limit.
    """
    query = select(AITask)
    
    if status:
        query = query.where(AITask.status == status)
    if task_type:
        query = query.where(AITask.task_type == task_type)
    
    query = query.order_by(AITask.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [
        {
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
        for task in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_ai_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get single AI task with full evidence.
    """
    task = await db.scalar(select(AITask).where(AITask.id == task_id))
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "player_uuid": task.player_uuid,
        "created_at": task.created_at.isoformat(),
        "expires_at": task.expires_at.isoformat(),
        "ai_summary": task.ai_summary,
        "ai_recommendation": task.ai_recommendation,
        "ai_confidence": task.ai_confidence,
        "evidence": task.evidence,
        "reviewed_by": task.reviewed_by,
        "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
        "action_taken": task.action_taken,
    }


@router.post("/tasks/{task_id}/approve")
async def approve_ai_task(
    task_id: int,
    body: ApproveTaskRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
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
    
    # Create audit log
    audit = AuditLog(
        actor=body.reviewed_by,
        actor_type="staff",
        action="ai_task.approved",
        target=str(task_id),
        details_json='{"task_id": ' + str(task_id) + ', "action_taken": "' + body.action_taken + '"}',
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(task)
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "player_uuid": task.player_uuid,
        "created_at": task.created_at.isoformat(),
        "expires_at": task.expires_at.isoformat(),
        "ai_summary": task.ai_summary,
        "ai_recommendation": task.ai_recommendation,
        "ai_confidence": task.ai_confidence,
        "evidence": task.evidence,
        "reviewed_by": task.reviewed_by,
        "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
        "action_taken": task.action_taken,
    }


@router.post("/tasks/{task_id}/deny")
async def deny_ai_task(
    task_id: int,
    body: DenyTaskRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
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
    
    # Create audit log
    audit = AuditLog(
        actor=body.reviewed_by,
        actor_type="staff",
        action="ai_task.denied",
        target=str(task_id),
        details_json='{"task_id": ' + str(task_id) + ', "reason": "' + (body.reason or "") + '"}',
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(task)
    
    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "player_uuid": task.player_uuid,
        "created_at": task.created_at.isoformat(),
        "expires_at": task.expires_at.isoformat(),
        "ai_summary": task.ai_summary,
        "ai_recommendation": task.ai_recommendation,
        "ai_confidence": task.ai_confidence,
        "evidence": task.evidence,
        "reviewed_by": task.reviewed_by,
        "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
        "action_taken": task.action_taken,
    }
