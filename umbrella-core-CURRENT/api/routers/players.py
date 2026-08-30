"""
api/routers/players.py — Player endpoints.

GET  /api/v1/players                    — list all players (with optional search by username)
GET  /api/v1/players/{uuid}             — get a single player by UUID
GET  /api/v1/players/{uuid}/full-profile — aggregated full profile (Task 1 / P15)

All responses require admin key or session authentication.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Any

from database import get_db
from models import Player, Punishment, Appeal, AltGroupMember, AltGroup, DiscordAccount
from api.dependencies.permissions import require_permission

# AnticheatViolation is added by Backend A. Import with fallback stub so this
# router compiles even if Backend A has not been merged yet.
try:
    from models.anticheat_violation import AnticheatViolation  # noqa: F401
    _HAS_ANTICHEAT = True
except ImportError:
    _HAS_ANTICHEAT = False

router = APIRouter(prefix="/api/v1/players", tags=["players"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class IPAddressSchema(BaseModel):
    id: str
    ip_address: str
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class PlayerSchema(BaseModel):
    uuid: str
    username: str
    first_seen: datetime
    last_seen: datetime
    playtime: int
    joins: int
    deaths: int
    risk_score: int
    suspicion_score: int
    discord_id: str | None

    class Config:
        from_attributes = True


class PlayerDetailSchema(PlayerSchema):
    ip_addresses: list[IPAddressSchema] = []

    class Config:
        from_attributes = True


# --- Full-profile sub-schemas ---

class VerificationSchema(BaseModel):
    discord_id: str
    discord_username: str | None
    linked_at: datetime | None
    status: str  # "verified" | "unverified"


class PunishmentHistoryItem(BaseModel):
    id: str
    type: str
    reason: str
    staff_id: str | None
    created_at: datetime
    expires_at: datetime | None
    active: bool
    # appeal_id: linked appeal if one exists — populated below
    appeal_id: str | None = None


class AnticheatCheckSummary(BaseModel):
    count: int
    avg_vl: float
    max_vl: int


class AnticheatTimelineItem(BaseModel):
    check_name: str
    vl: int
    verbose: str | None
    timestamp: datetime


class AnticheatHistorySchema(BaseModel):
    total_flags: int
    by_check: dict[str, AnticheatCheckSummary]
    timeline: list[AnticheatTimelineItem]


class AppealHistoryItem(BaseModel):
    id: str
    punishment_id: str
    status: str
    created_at: datetime
    action_taken: str | None = None
    handled_by: str | None = None
    ai_recommendation: str | None = None


class AltAccountItem(BaseModel):
    uuid: str
    username: str | None
    confidence: str | None  # group-level notes used as proxy
    cluster_type: str | None  # "confirmed" | "suspected"


class FullProfileResponse(BaseModel):
    player: dict[str, Any]
    verification: VerificationSchema | None
    punishment_history: list[PunishmentHistoryItem]
    anticheat_history: AnticheatHistorySchema
    appeal_history: list[AppealHistoryItem]
    alt_accounts: list[AltAccountItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _punishment_to_item(p: Punishment, appeal_map: dict[str, str]) -> PunishmentHistoryItem:
    return PunishmentHistoryItem(
        id=p.id,
        type=p.type,
        reason=p.reason,
        staff_id=p.staff_id,
        created_at=p.created_at,
        expires_at=p.expires_at,
        active=p.active,
        appeal_id=appeal_map.get(p.id),
    )


def _appeal_to_item(a: Appeal) -> AppealHistoryItem:
    return AppealHistoryItem(
        id=a.id,
        punishment_id=a.punishment_id,
        status=a.status,
        created_at=a.created_at,
        action_taken=getattr(a, "action_taken", None),
        handled_by=getattr(a, "handled_by", None),
        # ai_recommendation not stored on Appeal directly; leave None
        ai_recommendation=None,
    )


async def _query_punishments(db: AsyncSession, player_uuid: str) -> list[Punishment]:
    result = await db.execute(
        select(Punishment)
        .where(Punishment.player_uuid == player_uuid)
        .order_by(Punishment.created_at.desc())
    )
    return list(result.scalars().all())


async def _query_appeals(db: AsyncSession, player_uuid: str) -> list[Appeal]:
    result = await db.execute(
        select(Appeal)
        .where(Appeal.player_uuid == player_uuid)
        .order_by(Appeal.created_at.desc())
    )
    return list(result.scalars().all())


async def _query_discord(db: AsyncSession, player_uuid: str) -> DiscordAccount | None:
    return await db.scalar(
        select(DiscordAccount).where(DiscordAccount.player_uuid == player_uuid)
    )


async def _query_alt_group_members(db: AsyncSession, player_uuid: str) -> list[AltGroupMember]:
    result = await db.execute(
        select(AltGroupMember).where(AltGroupMember.player_uuid == player_uuid)
    )
    return list(result.scalars().all())


async def _query_anticheat(
    db: AsyncSession, player_uuid: str
) -> AnticheatHistorySchema:
    """
    Query AnticheatViolation for the last 30 days.
    Returns empty structure if Backend A model is not yet merged.
    """
    if not _HAS_ANTICHEAT:
        # Backend A not merged yet — return empty stub
        return AnticheatHistorySchema(total_flags=0, by_check={}, timeline=[])

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(AnticheatViolation)
        .where(
            AnticheatViolation.player_uuid == player_uuid,
            AnticheatViolation.timestamp >= cutoff,
        )
        .order_by(AnticheatViolation.timestamp.desc())
    )
    violations = list(result.scalars().all())

    by_check: dict[str, dict] = {}
    for v in violations:
        name = v.check_name
        if name not in by_check:
            by_check[name] = {"count": 0, "vl_sum": 0, "max_vl": 0}
        by_check[name]["count"] += 1
        by_check[name]["vl_sum"] += v.vl
        if v.vl > by_check[name]["max_vl"]:
            by_check[name]["max_vl"] = v.vl

    by_check_summary = {
        name: AnticheatCheckSummary(
            count=data["count"],
            avg_vl=round(data["vl_sum"] / data["count"], 2),
            max_vl=data["max_vl"],
        )
        for name, data in by_check.items()
    }

    timeline = [
        AnticheatTimelineItem(
            check_name=v.check_name,
            vl=v.vl,
            verbose=getattr(v, "verbose", None),
            timestamp=v.timestamp,
        )
        for v in violations[:50]
    ]

    return AnticheatHistorySchema(
        total_flags=len(violations),
        by_check=by_check_summary,
        timeline=timeline,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[PlayerSchema])
async def list_players(
    username: str | None = Query(None, description="Optional username substring to search"),
    skip: int = Query(0, ge=0, description="Number of players to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of players to return"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> list[PlayerSchema]:
    """
    List all players with optional username search.
    Supports pagination via skip and limit parameters.
    """
    query = select(Player)

    if username:
        query = query.where(Player.username.ilike(f"%{username}%"))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    players = result.scalars().all()

    return [PlayerSchema.model_validate(p) for p in players]


@router.get("/{uuid}/full-profile", response_model=FullProfileResponse)
async def get_player_full_profile(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> FullProfileResponse:
    """
    Aggregated full profile for a player — one call, all data.

    Queries in parallel:
      - Verification (DiscordAccount)
      - Punishment history
      - Appeals
      - AnticheatViolation (last 30 days) — stubbed if Backend A not merged
      - Alt group membership

    Returns assembled profile. 404 if player not found.
    """
    # Fetch player first — 404 gate
    player = await db.scalar(select(Player).where(Player.uuid == uuid))
    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{uuid}' not found")

    # Parallel queries
    punishments, appeals, discord_acct, alt_members, anticheat_hist = await asyncio.gather(
        _query_punishments(db, uuid),
        _query_appeals(db, uuid),
        _query_discord(db, uuid),
        _query_alt_group_members(db, uuid),
        _query_anticheat(db, uuid),
    )

    # Build punishment → appeal map (first appeal per punishment)
    appeal_map: dict[str, str] = {}
    for a in appeals:
        if a.punishment_id not in appeal_map:
            appeal_map[a.punishment_id] = a.id

    # Build verification block
    verification: VerificationSchema | None = None
    if discord_acct:
        verification = VerificationSchema(
            discord_id=discord_acct.discord_id,
            discord_username=discord_acct.discord_username,
            linked_at=discord_acct.linked_at,
            status="verified" if discord_acct.verified else "unverified",
        )

    # Build alt accounts block
    alt_accounts: list[AltAccountItem] = []
    if alt_members:
        group_ids = [m.group_id for m in alt_members]
        groups_result = await db.execute(
            select(AltGroup).where(AltGroup.id.in_(group_ids))
        )
        groups_by_id = {g.id: g for g in groups_result.scalars().all()}

        # Fetch all members of those groups (excluding this player)
        all_members_result = await db.execute(
            select(AltGroupMember).where(
                AltGroupMember.group_id.in_(group_ids),
                AltGroupMember.player_uuid != uuid,
            )
        )
        all_other_members = list(all_members_result.scalars().all())

        # Fetch player records for those UUIDs
        other_uuids = [m.player_uuid for m in all_other_members]
        if other_uuids:
            other_players_result = await db.execute(
                select(Player).where(Player.uuid.in_(other_uuids))
            )
            other_players_by_uuid = {p.uuid: p for p in other_players_result.scalars().all()}
        else:
            other_players_by_uuid = {}

        for member in all_other_members:
            group = groups_by_id.get(member.group_id)
            other_player = other_players_by_uuid.get(member.player_uuid)
            alt_accounts.append(
                AltAccountItem(
                    uuid=member.player_uuid,
                    username=other_player.username if other_player else None,
                    confidence=group.notes if group else None,
                    cluster_type="confirmed" if (group and group.confirmed) else "suspected",
                )
            )

    return FullProfileResponse(
        player={
            "uuid": player.uuid,
            "username": player.username,
            "first_seen": player.first_seen,
            "last_seen": player.last_seen,
            "playtime": player.playtime,
            "current_server": None,  # populated by plugin heartbeat layer, not in Player model
            "risk_score": player.risk_score,
            "suspicion_score": player.suspicion_score,
        },
        verification=verification,
        punishment_history=[_punishment_to_item(p, appeal_map) for p in punishments],
        anticheat_history=anticheat_hist,
        appeal_history=[_appeal_to_item(a) for a in appeals],
        alt_accounts=alt_accounts,
    )


class PlayerSnapshotRequest(BaseModel):
    uuid: str
    name: str
    ip: str | None = None
    brand: str | None = None
    ping: int | None = None
    protocol_version: int | None = None
    event: str | None = None  # "join" | "quit" | "snapshot"
    action: str | None = None


from api.middleware.auth import require_plugin_key

@router.post("/{uuid}/snapshot", status_code=200)
async def player_snapshot(
    uuid: str,
    body: PlayerSnapshotRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """
    Called by the Minecraft plugin on every player join/quit.
    Upserts the player record and logs the IP address.
    """
    from models.player import IPAddress
    import uuid as uuid_lib

    # AUDIT-2026-08-29 fix: uuid was used to create/update Player rows with
    # no format check at all (Player.uuid is a plain String(36), not a native
    # UUID column) — a malformed value from a buggy plugin build would be
    # silently persisted as a player record instead of being rejected.
    try:
        uuid_lib.UUID(uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"'{uuid}' is not a valid UUID")

    now = datetime.now(timezone.utc)
    event = body.event or body.action or "snapshot"

    # Upsert player
    result = await db.execute(select(Player).where(Player.uuid == uuid))
    player = result.scalar_one_or_none()

    if player is None:
        player = Player(
            uuid=uuid,
            username=body.name,
            first_seen=now,
            last_seen=now,
            joins=1 if event == "join" else 0,
        )
        db.add(player)
    else:
        player.username = body.name
        player.last_seen = now
        if event == "join":
            player.joins = (player.joins or 0) + 1

    await db.flush()

    # Upsert IP address if provided
    if body.ip and body.ip not in ("127.0.0.1", "0.0.0.0"):
        ip_result = await db.execute(
            select(IPAddress).where(
                IPAddress.player_uuid == uuid,
                IPAddress.ip_address == body.ip,
            )
        )
        ip_row = ip_result.scalar_one_or_none()
        if ip_row is None:
            db.add(IPAddress(
                id=str(uuid_lib.uuid4()),
                player_uuid=uuid,
                ip_address=body.ip,
                first_seen=now,
                last_seen=now,
            ))
        else:
            ip_row.last_seen = now

    await db.commit()
    return {"status": "ok", "uuid": uuid, "event": event}


@router.get("/{uuid}", response_model=PlayerDetailSchema)
async def get_player(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> PlayerDetailSchema:
    """Get a player by UUID with all related data (IP addresses)."""
    result = await db.execute(
        select(Player)
        .options(selectinload(Player.ip_addresses))
        .where(Player.uuid == uuid)
    )
    player = result.scalar_one_or_none()

    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{uuid}' not found")

    return PlayerDetailSchema.model_validate(player)
