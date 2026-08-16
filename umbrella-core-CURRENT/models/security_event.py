"""
models/security_event.py — Raw signal feed for threat detection
(Phase 9, item 4). See services/threat_detection_service.py's module
docstring for the scoping decision (this project's actual threat model,
not generic enterprise SIEM tooling) and how these rows turn into an
alert on the Phase 6 notification fabric.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    # auth_failure | rate_limit_violation | sandbox_violation
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    identifier: Mapped[str | None] = mapped_column(String(256), nullable=True)  # e.g. hashed API key, plugin_id
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    def __repr__(self) -> str:
        return f"<SecurityEvent type={self.event_type!r} ip={self.source_ip!r}>"
