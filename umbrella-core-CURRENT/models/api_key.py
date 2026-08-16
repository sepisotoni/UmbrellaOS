"""
models/api_key.py — Scoped, revocable API keys for machine-to-machine
access (CLI, Discord bot, external integrations), Phase 3.

The plaintext key is never stored — only its SHA-256 hash. A `key_prefix`
(the first 8 characters of the plaintext) is stored alongside it purely so
a UI can show "sk_umbr_a1b2c3d4..." to help an operator identify which key
is which without ever being able to reconstruct the full value from what's
stored.
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base
from models.user import User  # noqa: F401 - resolves the "User" forward reference in Mapped["User | None"] below


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)

    # Explicit permission keys this key carries — never "*"/superuser via
    # this path, by design: an API key is meant to be scoped to what a
    # specific integration actually needs, not a second admin-key
    # bootstrap tier. See services/api_key_service.py.
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")

    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    creator: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id!r} name={self.name!r} prefix={self.key_prefix!r}>"
