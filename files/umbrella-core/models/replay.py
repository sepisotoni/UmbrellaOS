"""
models/replay.py — Replay system models.

ReplaySession: Represents a replay capture session (e.g., triggered by a ban, mute, anticheat, report, or manual trigger).
ReplayEvent: Individual events captured during a replay session (movement, inventory, combat, command, damage, block).
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class ReplaySession(Base):
    __tablename__ = "replay_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    minecraft_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    incident_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["ReplayEvent"]] = relationship(
        "ReplayEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ReplayEvent(Base):
    __tablename__ = "replay_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    replay_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("replay_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    minecraft_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_data_json: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    world: Mapped[str | None] = mapped_column(String(128), nullable=True)

    session: Mapped["ReplaySession"] = relationship("ReplaySession", back_populates="events")
