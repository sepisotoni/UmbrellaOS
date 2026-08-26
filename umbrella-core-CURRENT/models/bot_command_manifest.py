"""
models/bot_command_manifest.py — Single-row table storing the Discord bot's
registered slash command manifest. The bot POSTs its full command list here
on startup (after syncing with Discord). The dashboard reads it via GET to
display real command data instead of hardcoded stubs.

Always id=1; upserted on every bot startup.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class BotCommandManifest(Base):
    __tablename__ = "bot_command_manifest"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    commands: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    pushed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
