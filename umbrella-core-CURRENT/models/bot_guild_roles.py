"""
models/bot_guild_roles.py — Single-row table storing the Discord bot's
guild mentionable role list. Bot POSTs on startup; dashboard reads to
populate the Role Mention dropdown in the broadcaster.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class BotGuildRoles(Base):
    __tablename__ = "bot_guild_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    roles: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    pushed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
