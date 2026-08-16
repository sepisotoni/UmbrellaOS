"""
models/investigation.py — Ported from Moo-assistant's models_moderation_intel.py
(Investigation, InvestigationFinding). `guild_id` dropped, matching every
other Phase 5 model.

Not ported: the intent-classifier-driven tool selection
(bot/ai/intent_service.py + bot/investigation/registry.py's
_INTENT_TOOL_MAP). umbrella-core's AI Tool Registry (registry/adapters/ai.py)
already exposes the full permitted tool list directly to the model via
list_tools() - a bespoke rule-based intent classifier to pre-select a
tool subset was solving a problem native LLM tool-calling doesn't have.
Each investigation tool is instead its own registered capability (see
capabilities/investigation.py), and `investigation.run` aggregates all of
them - the one remaining piece of value from Moo's registry.py, without
the intent-classification layer.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class Investigation(Base):
    """A record of an `investigation.run` call, aggregating one or more
    pluggable tool findings."""

    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requested_by: Mapped[str] = mapped_column(String(32))
    target_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvestigationFinding(Base):
    """A single pluggable tool's finding within an Investigation."""

    __tablename__ = "investigation_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    tool_key: Mapped[str] = mapped_column(String(100))
    finding_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
