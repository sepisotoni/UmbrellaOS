"""
models/anticheat_violation.py — Dedicated table for GrimAC anticheat flag records.

Each row represents a single flag event forwarded from the Minecraft plugin
via POST /api/v1/anticheat/flag.  The old approach shoehorned flags into
AITask rows; this model gives violations their own first-class table so
server_id filtering, per-check aggregation, and VL timelines all work cleanly.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class AnticheatViolation(Base):
    __tablename__ = "anticheat_violations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    player_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # server_id is nullable — old plugin versions do not send it.
    server_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    check_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    verbose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    vl: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        server_default=func.now(),
    )
