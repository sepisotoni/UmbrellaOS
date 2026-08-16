"""
services/player_risk/risk_score.py — Unified player risk score (Phase 5's
fourth "novel capability"): "one number/surface combining alt-detection,
anticheat signals, moderation history, and investigation findings."

No new infrastructure needed - every signal already exists:
- Anticheat/suspicion: models.alt_detection.SuspicionEvent (Minecraft-side,
  keyed by player_uuid).
- Alt detection: models.alt_detection.AltGroup/AltGroupMember (same key).
- Moderation history: models.moderation_intelligence.ModerationAction
  (Discord-side, keyed by discord user_id).
- Investigation findings: models.investigation.Investigation
  (Discord-side, keyed by target_user_id).

The one real piece of integration work: Minecraft-side signals are keyed
by player_uuid, Discord-side signals by discord_id - bridged via
models.discord.DiscordAccount, the same pre-existing link table
investigation's LinkedAccountTool already uses (see
services/investigation/tools.py). A player with no verified Discord link
still gets a score from the Minecraft-side signals alone - a missing
Discord link is not itself suspicious and isn't scored as such.

Deliberately a simple, explainable point-based weighting (config.settings'
risk_score_* values), not a trained model - the same philosophy as
services/operational_intelligence/crash_prevention.py: an auditable "+30
for a confirmed alt group, +15 for 3 moderation actions" is more useful to
a staff member deciding what to do about a player than an opaque score.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.alt_detection import AltGroup, AltGroupMember, SuspicionEvent
from models.discord import DiscordAccount
from models.investigation import Investigation
from models.moderation_intelligence import ModerationAction


@dataclass(frozen=True)
class RiskScoreBreakdown:
    anticheat_points: int
    confirmed_alt_group: bool
    moderation_action_count: int
    investigation_count: int
    anticheat_component: int
    alt_component: int
    moderation_component: int
    investigation_component: int


@dataclass(frozen=True)
class RiskScoreResult:
    player_uuid: str
    discord_id: str | None
    total_score: int  # 0-100
    breakdown: RiskScoreBreakdown
    reasoning: str


async def _resolve_discord_id(db: AsyncSession, player_uuid: str) -> str | None:
    stmt = select(DiscordAccount).where(DiscordAccount.player_uuid == player_uuid, DiscordAccount.verified.is_(True))
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    return account.discord_id if account is not None else None


async def _anticheat_points(db: AsyncSession, player_uuid: str) -> int:
    """Sum of unreviewed, non-false-positive SuspicionEvent points -
    reviewed-and-dismissed or explicitly false-positive events don't
    count, since a human already determined they weren't real signal."""
    stmt = select(SuspicionEvent).where(
        SuspicionEvent.player_uuid == player_uuid,
        SuspicionEvent.false_positive.is_(False),
    )
    result = await db.execute(stmt)
    events = list(result.scalars().all())
    return sum(e.points for e in events)


async def _is_confirmed_alt(db: AsyncSession, player_uuid: str) -> bool:
    stmt = (
        select(AltGroup)
        .join(AltGroupMember, AltGroupMember.group_id == AltGroup.id)
        .where(AltGroupMember.player_uuid == player_uuid, AltGroup.confirmed.is_(True))
    )
    result = await db.execute(stmt)
    return result.first() is not None


async def _moderation_action_count(db: AsyncSession, discord_id: str) -> int:
    stmt = select(ModerationAction).where(ModerationAction.user_id == discord_id)
    result = await db.execute(stmt)
    return len(list(result.scalars().all()))


async def _investigation_count(db: AsyncSession, discord_id: str) -> int:
    stmt = select(Investigation).where(Investigation.target_user_id == discord_id)
    result = await db.execute(stmt)
    return len(list(result.scalars().all()))


async def compute_risk_score(db: AsyncSession, player_uuid: str) -> RiskScoreResult:
    settings = get_settings()

    discord_id = await _resolve_discord_id(db, player_uuid)
    anticheat_points = await _anticheat_points(db, player_uuid)
    confirmed_alt = await _is_confirmed_alt(db, player_uuid)

    moderation_count = 0
    investigation_count = 0
    if discord_id is not None:
        moderation_count = await _moderation_action_count(db, discord_id)
        investigation_count = await _investigation_count(db, discord_id)

    anticheat_component = min(anticheat_points, settings.risk_score_anticheat_points_cap)
    alt_component = settings.risk_score_confirmed_alt_penalty if confirmed_alt else 0
    moderation_component = min(
        moderation_count * settings.risk_score_per_moderation_action, settings.risk_score_moderation_action_cap
    )
    investigation_component = min(
        investigation_count * settings.risk_score_per_investigation, settings.risk_score_investigation_cap
    )

    total = min(100, anticheat_component + alt_component + moderation_component + investigation_component)

    reasoning_parts = []
    if anticheat_component:
        reasoning_parts.append(f"{anticheat_component} points from unreviewed anticheat/suspicion signals")
    if alt_component:
        reasoning_parts.append(f"{alt_component} points for being in a confirmed alt group")
    if moderation_component:
        reasoning_parts.append(f"{moderation_component} points from {moderation_count} moderation action(s)")
    if investigation_component:
        reasoning_parts.append(f"{investigation_component} points from {investigation_count} investigation(s)")
    if discord_id is None:
        reasoning_parts.append(
            "no verified Discord link - moderation/investigation history unavailable, not itself a risk signal"
        )
    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No risk signals found for this player."

    return RiskScoreResult(
        player_uuid=player_uuid,
        discord_id=discord_id,
        total_score=total,
        breakdown=RiskScoreBreakdown(
            anticheat_points=anticheat_points,
            confirmed_alt_group=confirmed_alt,
            moderation_action_count=moderation_count,
            investigation_count=investigation_count,
            anticheat_component=anticheat_component,
            alt_component=alt_component,
            moderation_component=moderation_component,
            investigation_component=investigation_component,
        ),
        reasoning=reasoning,
    )
