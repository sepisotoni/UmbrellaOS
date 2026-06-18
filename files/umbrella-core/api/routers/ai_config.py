"""
api/routers/ai_config.py — AI Configuration API endpoints.

Handles AI-powered configuration requests and approvals.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import AIConfigAction
from api.middleware.auth import require_admin_key
from services.ai_config_service import process_ai_config_request, apply_config_action, AIConfigServiceError

router = APIRouter(prefix="/api/v1/ai/config", tags=["ai-config"])


class AIConfigRequest(BaseModel):
    action_type: str  # dashboard_layout, discord_config, plugin_config
    natural_language: str


class AIConfigResponse(BaseModel):
    id: int
    action_type: str
    natural_language_input: str
    ai_interpretation: str
    proposed_changes: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None
    applied_at: datetime | None
    error_message: str | None

    class Config:
        from_attributes = True


@router.post("/request", response_model=AIConfigResponse)
async def request_ai_config(
    body: AIConfigRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> AIConfigResponse:
    """
    Request AI-generated configuration.
    
    Uses OpenRouter API to interpret natural language and generate
    configuration suggestions that must be approved before applying.
    """
    try:
        config_action = await process_ai_config_request(
            action_type=body.action_type,
            natural_language=body.natural_language,
            db=db,
        )
        return AIConfigResponse.model_validate(config_action)
    except AIConfigServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pending", response_model=list[AIConfigResponse])
async def get_pending_configs(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[AIConfigResponse]:
    """
    Get all pending AI configuration actions.
    """
    result = await db.execute(
        select(AIConfigAction).where(AIConfigAction.status == "pending")
        .order_by(AIConfigAction.created_at.desc())
    )
    pending = result.scalars().all()
    return [AIConfigResponse.model_validate(action) for action in pending]


@router.post("/{id}/approve", response_model=AIConfigResponse)
async def approve_config(
    id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> AIConfigResponse:
    """
    Approve and apply an AI configuration action.
    """
    try:
        config_action = await apply_config_action(id, db)
        return AIConfigResponse.model_validate(config_action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/reject", response_model=AIConfigResponse)
async def reject_config(
    id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> AIConfigResponse:
    """
    Reject an AI configuration action.
    """
    result = await db.execute(select(AIConfigAction).where(AIConfigAction.id == id))
    config_action = result.scalar_one_or_none()
    
    if not config_action:
        raise HTTPException(status_code=404, detail="AI config action not found")
    
    if config_action.status != "pending":
        raise HTTPException(status_code=400, detail=f"Action is {config_action.status}, cannot reject")
    
    config_action.status = "rejected"
    config_action.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config_action)
    
    return AIConfigResponse.model_validate(config_action)
