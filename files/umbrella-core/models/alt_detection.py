"""
models/alt_detection.py — Alt detection and suspicion scoring models.

SuspicionEvent: Records suspicion score increases for players.
AltGroup: Groups of suspected alt accounts.
AltGroupMember: Players in an alt group.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class SuspicionEvent(Base):
    """Records suspicion score increases for players."""
    
    __tablename__ = "suspicion_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    false_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<SuspicionEvent id={self.id!r} player_uuid={self.player_uuid!r} trigger={self.trigger!r} points={self.points!r}>"


class AltGroup(Base):
    """Groups of suspected alt accounts."""
    
    __tablename__ = "alt_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<AltGroup id={self.id!r} confirmed={self.confirmed!r}>"


class AltGroupMember(Base):
    """Players in an alt group."""
    
    __tablename__ = "alt_group_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alt_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    added_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    def __repr__(self) -> str:
        return f"<AltGroupMember id={self.id!r} group_id={self.group_id!r} player_uuid={self.player_uuid!r}>"
