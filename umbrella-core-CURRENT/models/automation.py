"""
models/automation.py — Phase 4's automation domain: scheduled capability
invocations.

A Schedule is deliberately generic — it names a capability and a fixed set
of params to invoke it with on a cron expression, rather than being
"a backup schedule" or "a restart schedule" as distinct concepts. Anything
already reachable through the Capability Registry (Phase 0) becomes
schedulable for free, the same way it became CLI- and REST-reachable for
free — no new automation-specific plumbing per capability.
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    cron_expression: Mapped[str] = mapped_column(String(64), nullable=False)  # standard 5-field cron

    # Which capability to invoke and with what params — see module docstring
    # for why this is generic rather than backup/restart-specific.
    capability_name: Mapped[str] = mapped_column(String(128), nullable=False)
    capability_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # success | failed
    last_run_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Schedule id={self.id!r} name={self.name!r} cron={self.cron_expression!r}>"
