"""
models/analytics.py — Analytics event tracking and player statistics.

AnalyticsEvent: Raw event log for join, quit, death, kill, chat, command.
PlayerStat: Aggregated player metrics per period (daily, weekly, alltime).
"""
import uuid
from datetime import datetime, date

from sqlalchemy import BigInteger, DateTime, Date, Index, String, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class AnalyticsEvent(Base):
    """Raw analytics event log."""
    
    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    minecraft_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<AnalyticsEvent id={self.id!r} event_type={self.event_type!r} minecraft_uuid={self.minecraft_uuid!r}>"


class PlayerStat(Base):
    """Aggregated player statistics per period."""
    
    __tablename__ = "player_stats"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    minecraft_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("minecraft_uuid", "metric", "period", "period_start", name="uq_player_stats_player_metric_period"),
    )

    def __repr__(self) -> str:
        return f"<PlayerStat id={self.id!r} minecraft_uuid={self.minecraft_uuid!r} metric={self.metric!r} period={self.period!r}>"
