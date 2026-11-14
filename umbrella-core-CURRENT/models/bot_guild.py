"""Per-guild Discord bot discovery data and role/channel configuration."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class BotGuild(Base):
    __tablename__ = "bot_guilds"

    guild_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    channels: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    roles: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    staff_alert_channel_id: Mapped[str | None] = mapped_column(String(32))
    verified_role_id: Mapped[str | None] = mapped_column(String(32))
    owner_role_id: Mapped[str | None] = mapped_column(String(32))
    admin_role_id: Mapped[str | None] = mapped_column(String(32))
    moderator_role_id: Mapped[str | None] = mapped_column(String(32))
    helper_role_id: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pushed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
