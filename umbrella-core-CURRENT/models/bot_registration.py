"""
models/bot_registration.py — Single-row table tracking the Discord bot's
webhook callback URL. Core reads this when pushing events to the bot
(Phase 16B Task B). Always id=1; upserted via POST /api/v1/bot/register
on bot startup so restarts overwrite stale URLs automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class BotRegistration(Base):
    __tablename__ = "bot_registration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    callback_url: Mapped[str] = mapped_column(Text, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
