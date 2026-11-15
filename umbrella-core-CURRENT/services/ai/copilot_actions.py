"""Pending, human-confirmed moderation actions proposed by Copilot."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_tasks import AITask
from models.audit_log import AuditLog
from models.player import Player, Punishment

PROPOSAL_TTL = timedelta(minutes=10)
ACTION_PERMISSION = "moderation.ban"
ACTION_TASK_TYPE = "copilot_moderation_action"


class CopilotActionError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _proposal_from_task(task: AITask) -> dict[str, Any]:
    try:
        evidence = json.loads(task.evidence or "{}")
        proposal = evidence["copilot_action"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CopilotActionError("Stored Copilot action proposal is invalid", 409) from exc
    if (
        not isinstance(proposal, dict)
        or proposal.get("action") not in {"ban", "tempban", "unban"}
        or not isinstance(proposal.get("player_uuid"), str)
        or proposal.get("player_uuid") != task.player_uuid
        or not isinstance(proposal.get("player_name"), str)
        or not isinstance(proposal.get("reason"), str)
        or len(proposal["reason"]) > 500
    ):
        raise CopilotActionError("Stored Copilot action proposal is invalid", 409)
    if proposal["action"] == "tempban":
        duration_hours = proposal.get("duration_hours")
        expiry = proposal.get("expires_at")
        if (
            isinstance(duration_hours, bool)
            or not isinstance(duration_hours, int)
            or not 1 <= duration_hours <= 8760
            or not isinstance(expiry, str)
        ):
            raise CopilotActionError("Stored Copilot action proposal is invalid", 409)
        try:
            datetime.fromisoformat(expiry)
        except ValueError as exc:
            raise CopilotActionError(
                "Stored Copilot action proposal is invalid", 409
            ) from exc
    elif proposal.get("duration_hours") is not None or proposal.get("expires_at") is not None:
        raise CopilotActionError("Stored Copilot action proposal is invalid", 409)
    return proposal


async def propose_moderation_action(
    db: AsyncSession, args: dict[str, Any], *, actor: str, actor_type: str
) -> dict[str, Any]:
    action = args.get("action")
    if action not in {"ban", "tempban", "unban"}:
        raise CopilotActionError("Only ban, temporary ban, and unban proposals are supported")

    target = args.get("player_uuid") or args.get("username")
    if not isinstance(target, str) or not target.strip():
        raise CopilotActionError("A player UUID or username is required")
    target = target.strip()
    if len(target) > 64:
        raise CopilotActionError("Player identifier is too long")

    result = await db.scalars(
        select(Player)
        .where(
            or_(
                Player.uuid == target,
                func.lower(Player.username) == target.lower(),
            )
        )
        .limit(2)
    )
    players = list(result.all())
    if not players:
        raise CopilotActionError(f"No player found for {target!r}", 404)
    if len(players) > 1:
        raise CopilotActionError("Player identifier is ambiguous; use the UUID")
    player = players[0]

    reason = args.get("reason")
    if not isinstance(reason, str):
        raise CopilotActionError("A reason is required")
    reason = reason.strip()
    if action != "unban" and not reason:
        raise CopilotActionError("A reason is required for a ban")
    if len(reason) > 500:
        raise CopilotActionError("Reason must be 500 characters or fewer")

    now = datetime.now(timezone.utc)
    duration_hours = None
    expires_at = None
    if action == "tempban":
        duration_hours = args.get("duration_hours")
        if (
            isinstance(duration_hours, bool)
            or not isinstance(duration_hours, int)
            or not 1 <= duration_hours <= 8760
        ):
            raise CopilotActionError(
                "A temporary ban duration from 1 to 8760 hours is required"
            )
        expires_at = now + timedelta(hours=duration_hours)

    await expire_pending_proposals(db)
    existing_task = await db.scalar(
        select(AITask)
        .where(
            AITask.task_type == ACTION_TASK_TYPE,
            AITask.status == "pending",
            AITask.player_uuid == player.uuid,
        )
        .order_by(AITask.created_at.desc())
    )
    if existing_task:
        existing_proposal = _proposal_from_task(existing_task)
        if existing_proposal == {
            "action": action,
            "player_uuid": player.uuid,
            "player_name": player.username,
            "reason": reason,
            "duration_hours": duration_hours,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }:
            return {
                "status": "pending",
                "task_id": existing_task.id,
                **existing_proposal,
                "confirmation_required": True,
                "proposal_expires_at": _as_utc(existing_task.expires_at).isoformat(),
            }
        raise CopilotActionError(
            "A different moderation proposal for this player is already pending",
            409,
        )

    active_bans = list(
        (
            await db.scalars(
                select(Punishment).where(
                    Punishment.player_uuid == player.uuid,
                    Punishment.type.in_(("ban", "tempban")),
                    Punishment.active.is_(True),
                    or_(
                        Punishment.expires_at.is_(None),
                        Punishment.expires_at > now,
                    ),
                )
            )
        ).all()
    )
    if action == "unban" and not active_bans:
        raise CopilotActionError("This player has no active ban to revoke", 409)
    if action in {"ban", "tempban"} and active_bans:
        raise CopilotActionError("This player already has an active ban", 409)

    proposal = {
        "action": action,
        "player_uuid": player.uuid,
        "player_name": player.username,
        "reason": reason,
        "duration_hours": duration_hours,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }
    task = AITask(
        task_type=ACTION_TASK_TYPE,
        status="pending",
        player_uuid=player.uuid,
        created_at=now,
        expires_at=now + PROPOSAL_TTL,
        ai_summary=f"Copilot proposes {action} for {player.username}: {reason or 'No reason provided'}",
        ai_recommendation=action,
        ai_confidence=0.0,
        evidence=json.dumps({"copilot_action": proposal}),
    )
    db.add(task)
    await db.flush()
    db.add(
        AuditLog(
            actor=actor,
            actor_type=actor_type,
            action="ai_action.proposed",
            target=str(task.id),
            details_json=json.dumps(
                {
                    "task_id": task.id,
                    "action": action,
                    "player_uuid": player.uuid,
                    "expires_at": task.expires_at.isoformat(),
                }
            ),
        )
    )
    return {
        "status": "pending",
        "task_id": task.id,
        **proposal,
        "confirmation_required": True,
        "proposal_expires_at": task.expires_at.isoformat(),
    }


async def expire_pending_proposals(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(AITask)
        .where(
            AITask.task_type == ACTION_TASK_TYPE,
            AITask.status == "pending",
            AITask.expires_at <= now,
        )
        .values(status="expired", reviewed_at=now, action_taken="Expired without execution")
    )


async def execute_proposal(
    db: AsyncSession,
    task: AITask,
    *,
    actor: str,
    actor_type: str,
) -> dict[str, Any]:
    if task.task_type != ACTION_TASK_TYPE:
        raise CopilotActionError("Task is not a Copilot moderation action", 409)
    if task.status != "pending":
        raise CopilotActionError("Action proposal is no longer pending", 409)

    now = datetime.now(timezone.utc)
    if _as_utc(task.expires_at) <= now:
        task.status = "expired"
        task.reviewed_at = now
        task.action_taken = "Expired without execution"
        await db.flush()
        raise CopilotActionError("Action proposal has expired", 410)

    proposal = _proposal_from_task(task)
    action = proposal["action"]
    player = await db.scalar(
        select(Player)
        .where(Player.uuid == proposal["player_uuid"])
        .with_for_update()
    )
    if player is None:
        raise CopilotActionError("The target player no longer exists", 404)

    active_bans = list(
        (
            await db.scalars(
                select(Punishment)
                .where(
                    Punishment.player_uuid == player.uuid,
                    Punishment.type.in_(("ban", "tempban")),
                    Punishment.active.is_(True),
                    or_(
                        Punishment.expires_at.is_(None),
                        Punishment.expires_at > now,
                    ),
                )
                .with_for_update()
            )
        ).all()
    )
    if action == "unban":
        if not active_bans:
            raise CopilotActionError("This player no longer has an active ban", 409)
        for ban in active_bans:
            ban.active = False
            ban.status = "REVOKED"
    else:
        if active_bans:
            raise CopilotActionError("This player already has an active ban", 409)
        expires_at = proposal.get("expires_at")
        parsed_expiry = (
            datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else None
        )
        if action == "tempban" and (
            parsed_expiry is None or _as_utc(parsed_expiry) <= now
        ):
            raise CopilotActionError("Temporary ban proposal has an invalid expiry", 409)
        db.add(
            Punishment(
                player_uuid=player.uuid,
                staff_id=actor if actor_type == "staff" else None,
                type=action,
                reason=proposal["reason"],
                expires_at=parsed_expiry,
                active=True,
                status="ACTIVE",
            )
        )

    task.status = "approved"
    task.reviewed_by = actor[:64]
    task.reviewed_at = now
    task.action_taken = f"{action} executed for {player.username}"[:256]
    db.add(
        AuditLog(
            actor=actor,
            actor_type=actor_type,
            action="ai_action.executed",
            target=str(task.id),
            details_json=json.dumps(
                {
                    "task_id": task.id,
                    "action": action,
                    "player_uuid": player.uuid,
                    "reason": proposal["reason"],
                    "expires_at": proposal.get("expires_at"),
                }
            ),
        )
    )
    await db.flush()
    return {
        "task_id": task.id,
        "action": action,
        "player_uuid": player.uuid,
        "player_name": player.username,
        "status": task.status,
    }


async def decline_proposal(
    db: AsyncSession,
    task: AITask,
    *,
    actor: str,
    actor_type: str,
) -> None:
    if task.task_type != ACTION_TASK_TYPE:
        raise CopilotActionError("Task is not a Copilot moderation action", 409)
    if task.status != "pending":
        raise CopilotActionError("Action proposal is no longer pending", 409)
    now = datetime.now(timezone.utc)
    if _as_utc(task.expires_at) <= now:
        task.status = "expired"
        task.reviewed_at = now
        task.action_taken = "Expired without execution"
        await db.flush()
        raise CopilotActionError("Action proposal has expired", 410)
    task.status = "denied"
    task.reviewed_by = actor[:64]
    task.reviewed_at = now
    task.action_taken = "Declined by staff"
    db.add(
        AuditLog(
            actor=actor,
            actor_type=actor_type,
            action="ai_action.declined",
            target=str(task.id),
            details_json=json.dumps({"task_id": task.id}),
        )
    )
