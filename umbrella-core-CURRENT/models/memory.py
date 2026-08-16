"""
models/memory.py — Ported from Moo-assistant's models_ai.py (MemoryScope,
MemoryEntry). `guild_id` dropped, matching every other Phase 5 model (see
models/moderation_intelligence.py's module docstring).
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class MemoryScope(str, enum.Enum):
    SHORT_TERM = "short_term"  # conversational, expires quickly (minutes)
    SERVER = "server"  # facts about the server, rarely expires
    OPERATIONAL = "operational"  # recurring issues/resolutions staff care about, rarely expires


class MemoryEntry(Base):
    """Key/value memory store.

    `key` is an application-defined namespaced string, e.g.:
      - short_term:  "conversation:<channel_id>:<user_id>"
      - server:      "fact:server_ip"
      - operational: "recurring:<topic_key>"
    """

    __tablename__ = "memory_entries"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_memory_scope_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[MemoryScope] = mapped_column(Enum(MemoryScope), index=True)
    key: Mapped[str] = mapped_column(String(300))
    value: Mapped[str] = mapped_column(Text)  # free-form text or JSON-encoded payload
    hit_count: Mapped[int] = mapped_column(Integer, default=1)  # how many times this has recurred
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
