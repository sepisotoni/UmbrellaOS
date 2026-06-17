"""
services/snapshot_service.py — Snapshot system service.

Methods for managing player snapshots.
"""
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import PlayerSnapshot, ReplaySession


VALID_TRIGGERS = {"scheduled", "incident", "quit", "manual"}


async def create_snapshot(
    db: AsyncSession,
    minecraft_uuid: str,
    trigger: str = "scheduled",
    health: float | None = None,
    food: int | None = None,
    xp: float | None = None,
    inventory: dict | None = None,
    armor: dict | None = None,
    offhand: dict | None = None,
    x: float | None = None,
    y: float | None = None,
    z: float | None = None,
    yaw: float | None = None,
    pitch: float | None = None,
    world: str | None = None,
    dimension: str | None = None,
    replay_id: str | None = None,
    timestamp: datetime | None = None,
) -> PlayerSnapshot:
    """
    Create a new player snapshot.
    inventory, armor, offhand are dicts; store as JSON strings.
    timestamp defaults to utcnow() if not provided.
    Validates trigger is one of the four allowed values; raise ValueError if not.
    """
    if trigger not in VALID_TRIGGERS:
        raise ValueError(f"Invalid trigger: {trigger}. Must be one of {VALID_TRIGGERS}")

    if timestamp is None:
        timestamp = datetime.utcnow()

    snapshot = PlayerSnapshot(
        minecraft_uuid=minecraft_uuid,
        timestamp=timestamp,
        trigger=trigger,
        health=health,
        food=food,
        xp=xp,
        inventory_json=json.dumps(inventory) if inventory else None,
        armor_json=json.dumps(armor) if armor else None,
        offhand_json=json.dumps(offhand) if offhand else None,
        x=x,
        y=y,
        z=z,
        yaw=yaw,
        pitch=pitch,
        world=world,
        dimension=dimension,
        replay_id=replay_id,
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def get_snapshot(
    db: AsyncSession,
    snapshot_id: str,
) -> dict | None:
    """
    Get a snapshot as a dict.
    Returns None if not found.
    Dict fields: all columns; inventory_json, armor_json, offhand_json returned
    as raw JSON strings (callers parse if needed).
    """
    result = await db.execute(
        select(PlayerSnapshot).where(PlayerSnapshot.id == snapshot_id)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "minecraft_uuid": snapshot.minecraft_uuid,
        "timestamp": snapshot.timestamp.isoformat(),
        "trigger": snapshot.trigger,
        "health": snapshot.health,
        "food": snapshot.food,
        "xp": snapshot.xp,
        "inventory_json": snapshot.inventory_json,
        "armor_json": snapshot.armor_json,
        "offhand_json": snapshot.offhand_json,
        "x": snapshot.x,
        "y": snapshot.y,
        "z": snapshot.z,
        "yaw": snapshot.yaw,
        "pitch": snapshot.pitch,
        "world": snapshot.world,
        "dimension": snapshot.dimension,
        "replay_id": snapshot.replay_id,
    }


async def list_snapshots(
    db: AsyncSession,
    minecraft_uuid: str,
    limit: int = 20,
    offset: int = 0,
    trigger: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict]:
    """
    List snapshots for a player, newest first.
    Optional filters: trigger, since (datetime), until (datetime).
    Paginated with limit/offset.
    """
    query = select(PlayerSnapshot).where(PlayerSnapshot.minecraft_uuid == minecraft_uuid)

    if trigger:
        query = query.where(PlayerSnapshot.trigger == trigger)
    if since:
        query = query.where(PlayerSnapshot.timestamp >= since)
    if until:
        query = query.where(PlayerSnapshot.timestamp <= until)

    query = query.order_by(PlayerSnapshot.timestamp.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    return [
        {
            "id": snapshot.id,
            "minecraft_uuid": snapshot.minecraft_uuid,
            "timestamp": snapshot.timestamp.isoformat(),
            "trigger": snapshot.trigger,
            "health": snapshot.health,
            "food": snapshot.food,
            "xp": snapshot.xp,
            "inventory_json": snapshot.inventory_json,
            "armor_json": snapshot.armor_json,
            "offhand_json": snapshot.offhand_json,
            "x": snapshot.x,
            "y": snapshot.y,
            "z": snapshot.z,
            "yaw": snapshot.yaw,
            "pitch": snapshot.pitch,
            "world": snapshot.world,
            "dimension": snapshot.dimension,
            "replay_id": snapshot.replay_id,
        }
        for snapshot in snapshots
    ]


async def get_latest_snapshot(
    db: AsyncSession,
    minecraft_uuid: str,
) -> dict | None:
    """
    Get the single most recent snapshot for the player.
    Returns None if no snapshots exist.
    """
    query = (
        select(PlayerSnapshot)
        .where(PlayerSnapshot.minecraft_uuid == minecraft_uuid)
        .order_by(PlayerSnapshot.timestamp.desc())
        .limit(1)
    )
    result = await db.execute(query)
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "minecraft_uuid": snapshot.minecraft_uuid,
        "timestamp": snapshot.timestamp.isoformat(),
        "trigger": snapshot.trigger,
        "health": snapshot.health,
        "food": snapshot.food,
        "xp": snapshot.xp,
        "inventory_json": snapshot.inventory_json,
        "armor_json": snapshot.armor_json,
        "offhand_json": snapshot.offhand_json,
        "x": snapshot.x,
        "y": snapshot.y,
        "z": snapshot.z,
        "yaw": snapshot.yaw,
        "pitch": snapshot.pitch,
        "world": snapshot.world,
        "dimension": snapshot.dimension,
        "replay_id": snapshot.replay_id,
    }


async def get_snapshots_near_replay(
    db: AsyncSession,
    replay_id: str,
    window_minutes: int = 10,
) -> list[dict]:
    """
    Look up the ReplaySession by replay_id to get incident_at.
    Returns all snapshots for the same minecraft_uuid within ±window_minutes
    of incident_at, ordered by timestamp ASC.
    Returns [] if replay not found.
    """
    # Get the replay session
    result = await db.execute(
        select(ReplaySession).where(ReplaySession.id == replay_id)
    )
    replay = result.scalar_one_or_none()
    if not replay:
        return []

    # Calculate time window
    window = timedelta(minutes=window_minutes)
    start_time = replay.incident_at - window
    end_time = replay.incident_at + window

    # Get snapshots for the same player within the time window
    query = (
        select(PlayerSnapshot)
        .where(PlayerSnapshot.minecraft_uuid == replay.minecraft_uuid)
        .where(PlayerSnapshot.timestamp >= start_time)
        .where(PlayerSnapshot.timestamp <= end_time)
        .order_by(PlayerSnapshot.timestamp.asc())
    )
    result = await db.execute(query)
    snapshots = result.scalars().all()

    return [
        {
            "id": snapshot.id,
            "minecraft_uuid": snapshot.minecraft_uuid,
            "timestamp": snapshot.timestamp.isoformat(),
            "trigger": snapshot.trigger,
            "health": snapshot.health,
            "food": snapshot.food,
            "xp": snapshot.xp,
            "inventory_json": snapshot.inventory_json,
            "armor_json": snapshot.armor_json,
            "offhand_json": snapshot.offhand_json,
            "x": snapshot.x,
            "y": snapshot.y,
            "z": snapshot.z,
            "yaw": snapshot.yaw,
            "pitch": snapshot.pitch,
            "world": snapshot.world,
            "dimension": snapshot.dimension,
            "replay_id": snapshot.replay_id,
        }
        for snapshot in snapshots
    ]
