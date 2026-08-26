"""
models/bot_guild_channels.py — Single-row table storing the Discord bot's
guild text channel list. The bot POSTs on startup; dashboard reads to
populate the broadcaster dropdown instead of relying on manually-configured
setting keys.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class BotGuildChannels(Base):
    __tablename__ = "bot_guild_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    channels: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    pushed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
