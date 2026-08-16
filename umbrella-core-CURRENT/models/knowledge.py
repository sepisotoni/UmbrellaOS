"""
models/knowledge.py — Staff-maintained reference data investigation tools
read from. Ported from Moo-assistant's models_moderation_intel.py
(KnownIssue, WhitelistStatus, WhitelistEntry only — LinkedAccount is
deliberately NOT ported: umbrella-core already has models.discord.DiscordAccount,
which is the exact same "Discord user <-> in-game account" link, just
pre-existing since Phase 3. Porting a second, separate LinkedAccount table
would create two inconsistent sources of truth for the same fact.

`guild_id` dropped from every table, matching every other Phase 5 model
(see models/moderation_intelligence.py's module docstring for why).

No external server-status/whitelist-management API integration exists yet
in this skeleton, same as the source — wire a real one in here when one is
available.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class KnowledgeReviewStatus(str, enum.Enum):
    """Direct posts in a knowledge channel are auto-approved (a human
    already curated them by choosing to post there). AI-suggested or
    staff-submitted *corrections* start PENDING and only affect retrieval
    once approved - a pending/rejected correction can never silently
    change what the AI tells members."""

    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class KnowledgeEntry(Base):
    """A message from a designated knowledge channel (which channels count
    is dashboard-configurable, see config.settings.knowledge_channel_names -
    unlike the source, which hardcoded one Discord server's own channel
    names as a Python constant)."""

    __tablename__ = "knowledge_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id: Mapped[str] = mapped_column(String(32), index=True)
    channel_name: Mapped[str] = mapped_column(String(200))
    discord_message_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    author_id: Mapped[str] = mapped_column(String(32))
    author_name: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    review_status: Mapped[KnowledgeReviewStatus] = mapped_column(
        Enum(KnowledgeReviewStatus), default=KnowledgeReviewStatus.APPROVED, index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # If this entry is a proposed correction, points at the entry it would replace.
    corrects_entry_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_entries.id", ondelete="SET NULL"), nullable=True
    )
    # Set once a newer, approved entry has superseded this one (kept for
    # history, excluded from retrieval).
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_entries.id", ondelete="SET NULL"), nullable=True
    )


class KnowledgeVersion(Base):
    """Append-only history of a KnowledgeEntry's content over time - the
    *previous* content is archived here before an edit or an approved
    correction overwrites the live row, so staff can always see how an
    answer evolved."""

    __tablename__ = "knowledge_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_entries.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    edited_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnownIssue(Base):
    """A known server issue staff have logged (e.g. "EU servers down for maintenance")."""

    __tablename__ = "known_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WhitelistStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class WhitelistEntry(Base):
    """
    Whitelist application/status for an in-game username. Deliberately
    keyed by the raw `ingame_username` string, not a FK to models.player.Player -
    a whitelist application is often for someone who hasn't joined the
    server yet, so no Player row exists for them at application time.
    """

    __tablename__ = "whitelist_entries"
    __table_args__ = (UniqueConstraint("ingame_username", name="uq_whitelist_entries_username"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ingame_username: Mapped[str] = mapped_column(String(100))
    discord_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[WhitelistStatus] = mapped_column(Enum(WhitelistStatus), default=WhitelistStatus.PENDING)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
