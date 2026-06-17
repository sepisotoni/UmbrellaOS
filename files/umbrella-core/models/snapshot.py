"""
models/snapshot.py — Player snapshot model.

PlayerSnapshot: Represents a point-in-time capture of a player's state.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class PlayerSnapshot(Base):
    __tablename__ = "player_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    minecraft_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    health: Mapped[float | None] = mapped_column(Float, nullable=True)
    food: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp: Mapped[float | None] = mapped_column(Float, nullable=True)
    inventory_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    armor_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    offhand_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    x: Mapped[float | None] = mapped_column(Float, nullable=True)
    y: Mapped[float | None] = mapped_column(Float, nullable=True)
    z: Mapped[float | None] = mapped_column(Float, nullable=True)
    yaw: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch: Mapped[float | None] = mapped_column(Float, nullable=True)
    world: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dimension: Mapped[str | None] = mapped_column(String(64), nullable=True)
    replay_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("replay_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
