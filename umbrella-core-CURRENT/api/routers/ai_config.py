"""
api/routers/ai_config.py — AI Configuration API endpoints.

Handles AI-powered configuration requests and approvals.
"""
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone

from database import get_db
from models import AIConfigAction
from models.ai import AIModelConfig
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
        msg = str(e)
        # "no provider available" is a service outage (503), not a bad request (400)
        status = 503 if "No AI provider available" in msg else 400
        raise HTTPException(status_code=status, detail=msg)


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
    config_action.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(config_action)
    
    return AIConfigResponse.model_validate(config_action)


# ---------------------------------------------------------------------------
# Per-task AI model configuration  (P16C Task 1)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Per-task AI model configuration  (P16C Task 1)
#
# Bug fixed: the old implementation stored task→provider assignments as a
# JSON blob in the settings table (key "ai.task_config") which the
# ModelRouter never reads — it reads ai_model_configs rows.  So any change
# made via POST /config/tasks was silently stored but had zero effect on
# routing.
#
# Fix: GET /config/tasks reads from ai_model_configs (grouped by task_type,
# returning the top two rows by priority as "primary" and "failover").
# POST /config/tasks writes new rows to ai_model_configs (or updates
# existing ones) so the ModelRouter immediately sees the change.
#
# VALID_PROVIDERS is also restricted to providers actually registered in
# ProviderFactory — the old list included "openai" and "deepseek" which
# have never been implemented and would silently 503 if selected.
# ---------------------------------------------------------------------------

# These must match provider_factory._PROVIDER_REGISTRY keys exactly.
VALID_PROVIDERS = {"gemini", "anthropic", "openrouter"}

KNOWN_TASK_TYPES = {
    "player_review", "appeal_review", "copilot",
    "crash_risk", "chat_review", "moderation_review",
}

# Default model strings per provider — used when creating new ai_model_configs rows.
_DEFAULT_MODELS: dict[str, str] = {
    "gemini":      "gemini-1.5-flash",
    "anthropic":   "claude-haiku-4-5-20251001",
    "openrouter":  "openai/gpt-4o-mini",
}


class TaskModelAssignment(BaseModel):
    primary: str | None = None
    failover: str | None = None


class TaskConfigResponse(BaseModel):
    player_review: TaskModelAssignment = TaskModelAssignment()
    appeal_review: TaskModelAssignment = TaskModelAssignment()
    copilot: TaskModelAssignment = TaskModelAssignment()
    crash_risk: TaskModelAssignment = TaskModelAssignment()
    chat_review: TaskModelAssignment = TaskModelAssignment()
    moderation_review: TaskModelAssignment = TaskModelAssignment()


class TaskConfigUpdate(BaseModel):
    task: str
    primary: str
    failover: str | None = None


async def _load_model_configs(db: AsyncSession) -> dict[str, list]:
    """Return ai_model_configs rows grouped by task_type, sorted by priority."""
    result = await db.execute(
        select(AIModelConfig)
        .where(AIModelConfig.enabled.is_(True))
        .order_by(AIModelConfig.task_type, AIModelConfig.priority)
    )
    rows = result.scalars().all()
    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row.task_type, []).append(row)
    return grouped


@router.get("/tasks", response_model=TaskConfigResponse)
async def get_task_config(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("settings.manage")),
) -> TaskConfigResponse:
    """Return per-task AI model assignments, read from ai_model_configs table.

    Previously this read from a settings JSON blob that the ModelRouter
    never consulted — now it reads the actual table the router uses.
    """
    grouped = await _load_model_configs(db)

    def _assignment(task: str) -> TaskModelAssignment:
        rows = grouped.get(task, [])
        primary = rows[0].provider if len(rows) >= 1 else None
        failover = rows[1].provider if len(rows) >= 2 else None
        return TaskModelAssignment(primary=primary, failover=failover)

    return TaskConfigResponse(
        player_review=_assignment("player_review"),
        appeal_review=_assignment("appeal_review"),
        copilot=_assignment("copilot"),
        crash_risk=_assignment("crash_risk"),
        chat_review=_assignment("chat_review"),
        moderation_review=_assignment("moderation_review"),
    )


@router.post("/tasks", response_model=TaskConfigResponse)
async def update_task_config(
    body: TaskConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("settings.manage")),
) -> TaskConfigResponse:
    """Update primary/failover provider for a task by writing to ai_model_configs.

    Previously stored to a settings JSON blob the ModelRouter never read,
    so changes had zero effect on routing. Now writes directly to the table
    the ModelRouter queries so routing changes take effect immediately.
    """
    if body.task not in KNOWN_TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown task type: {body.task!r}. Valid: {sorted(KNOWN_TASK_TYPES)}")
    if body.primary not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.primary!r}. Valid: {sorted(VALID_PROVIDERS)}")
    if body.failover is not None and body.failover not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown failover provider: {body.failover!r}. Valid: {sorted(VALID_PROVIDERS)}")

    # Load all existing rows for this task_type
    result = await db.execute(
        select(AIModelConfig)
        .where(AIModelConfig.task_type == body.task)
        .order_by(AIModelConfig.priority)
    )
    existing = result.scalars().all()

    # We maintain at most 2 rows (priority 10=primary, 20=failover).
    # Find or create them.
    primary_row = next((r for r in existing if r.priority == 10), None)
    failover_row = next((r for r in existing if r.priority == 20), None)

    # Upsert primary
    if primary_row:
        primary_row.provider = body.primary
        primary_row.model_name = _DEFAULT_MODELS.get(body.primary, body.primary)
        primary_row.enabled = True
        primary_row.is_healthy = True
        primary_row.consecutive_failures = 0
    else:
        db.add(AIModelConfig(
            id=str(uuid.uuid4()),
            provider=body.primary,
            model_name=_DEFAULT_MODELS.get(body.primary, body.primary),
            task_type=body.task,
            priority=10,
            enabled=True,
            is_healthy=True,
            consecutive_failures=0,
        ))

    # Upsert or disable failover
    if body.failover:
        if failover_row:
            failover_row.provider = body.failover
            failover_row.model_name = _DEFAULT_MODELS.get(body.failover, body.failover)
            failover_row.enabled = True
            failover_row.is_healthy = True
            failover_row.consecutive_failures = 0
        else:
            db.add(AIModelConfig(
                id=str(uuid.uuid4()),
                provider=body.failover,
                model_name=_DEFAULT_MODELS.get(body.failover, body.failover),
                task_type=body.task,
                priority=20,
                enabled=True,
                is_healthy=True,
                consecutive_failures=0,
            ))
    elif failover_row:
        # Failover was cleared — disable it rather than deleting so health history is preserved
        failover_row.enabled = False

    await db.commit()

    grouped = await _load_model_configs(db)

    def _assignment(task: str) -> TaskModelAssignment:
        rows = grouped.get(task, [])
        p = rows[0].provider if len(rows) >= 1 else None
        f = rows[1].provider if len(rows) >= 2 else None
        return TaskModelAssignment(primary=p, failover=f)

    return TaskConfigResponse(
        player_review=_assignment("player_review"),
        appeal_review=_assignment("appeal_review"),
        copilot=_assignment("copilot"),
        crash_risk=_assignment("crash_risk"),
        chat_review=_assignment("chat_review"),
        moderation_review=_assignment("moderation_review"),
    )
