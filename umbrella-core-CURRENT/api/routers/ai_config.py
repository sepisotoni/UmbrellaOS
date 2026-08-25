"""
api/routers/ai_config.py — AI Configuration API endpoints.

Handles AI-powered configuration requests and approvals.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import AIConfigAction
from api.dependencies.permissions import require_permission
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
    _auth=Depends(require_permission("settings.manage")),
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
    _auth=Depends(require_permission("settings.manage")),
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
    _auth=Depends(require_permission("settings.manage")),
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
    _auth=Depends(require_permission("settings.manage")),
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


# ---------------------------------------------------------------------------
# Per-task AI model configuration  (P16C Task 1)
# ---------------------------------------------------------------------------

VALID_PROVIDERS = {"gemini", "anthropic", "openai", "deepseek", "openrouter"}

TASK_DEFAULTS: dict[str, dict] = {
    "player_review":  {"primary": "gemini",    "failover": "openrouter"},
    "appeal_review":  {"primary": "anthropic", "failover": "gemini"},
    "copilot":        {"primary": "gemini",    "failover": "openrouter"},
    "crash_risk":     {"primary": "gemini",    "failover": None},
    "chat_responder": {"primary": "openrouter","failover": None},
}

_SETTINGS_KEY = "ai.task_config"


class TaskModelAssignment(BaseModel):
    primary: str
    failover: str | None = None


class TaskConfigResponse(BaseModel):
    player_review: TaskModelAssignment
    appeal_review: TaskModelAssignment
    copilot: TaskModelAssignment
    crash_risk: TaskModelAssignment
    chat_responder: TaskModelAssignment


class TaskConfigUpdate(BaseModel):
    task: str
    primary: str
    failover: str | None = None


async def _read_task_config(db: AsyncSession) -> dict[str, dict]:
    """Load task config from settings, falling back to defaults."""
    from services.settings_service import SettingsService
    raw = await SettingsService.get_value(db, _SETTINGS_KEY)
    if raw:
        try:
            stored = json.loads(raw)
            # Merge with defaults so newly-added tasks always have an entry
            return {**TASK_DEFAULTS, **stored}
        except (json.JSONDecodeError, TypeError):
            pass
    return dict(TASK_DEFAULTS)


async def _write_task_config(db: AsyncSession, config: dict[str, dict]) -> None:
    from services.settings_service import SettingsService
    await SettingsService.set_value(
        db, _SETTINGS_KEY, json.dumps(config), category="ai", actor="system"
    )
    await db.commit()


@router.get("/tasks", response_model=TaskConfigResponse)
async def get_task_config(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("settings.manage")),
) -> TaskConfigResponse:
    """Return the per-task AI model assignments."""
    config = await _read_task_config(db)
    return TaskConfigResponse(
        **{task: TaskModelAssignment(**vals) for task, vals in config.items()}
    )


@router.post("/tasks", response_model=TaskConfigResponse)
async def update_task_config(
    body: TaskConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("settings.manage")),
) -> TaskConfigResponse:
    """Update the primary/failover provider for a single task."""
    if body.task not in TASK_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Unknown task: {body.task!r}")
    if body.primary not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.primary!r}")
    if body.failover is not None and body.failover not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown failover provider: {body.failover!r}")

    config = await _read_task_config(db)
    config[body.task] = {"primary": body.primary, "failover": body.failover}
    await _write_task_config(db, config)

    return TaskConfigResponse(
        **{task: TaskModelAssignment(**vals) for task, vals in config.items()}
    )
