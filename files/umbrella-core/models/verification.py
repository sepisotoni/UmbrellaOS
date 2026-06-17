"""
models/verification.py — Player verification system models.

VerificationCode: Stores 6-digit codes for Discord-based player verification.
"""
from datetime import datetime, timedelta

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class VerificationCode(Base):
    """Stores verification codes for Discord-based player verification."""
    
    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    player_username: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.utcnow() + timedelta(minutes=10)
    )
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    def __repr__(self) -> str:
        return f"<VerificationCode id={self.id!r} player_uuid={self.player_uuid!r} code={self.code!r}>"
