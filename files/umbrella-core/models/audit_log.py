"""
models/audit_log.py — Append-only audit trail.

Design decisions:
- NEVER update or delete audit records. Insert only.
- actor_type distinguishes who performed the action:
    "staff"   — a human staff member (identified by Discord ID / username)
    "plugin"  — the Minecraft plugin (automated)
    "bot"     — the Discord bot (automated)
    "system"  — internal background job
    "ai"      — AI task pipeline
- details_json stores arbitrary context as a JSON string so
  we never lose information, even for future action types.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from database.engine import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Who performed the action
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="system"
    )  # staff | plugin | bot | system | ai

    # What happened
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Who/what was affected (optional)
    target: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Arbitrary JSON context — never null, use "{}" if empty
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # Timestamp — no updated_at: audit records are immutable
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action!r} actor={self.actor!r}>"
