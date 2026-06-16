"""
models/user.py — User and Staff authentication models.

User: Staff account with Discord ID
Staff: Role assignment and permissions
Session: Token-based session tracking
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class User(Base):
    """Staff user account linked to Discord."""
    
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    discord_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} discord_id={self.discord_id!r} username={self.username!r}>"


class Session(Base):
    """User session token for web/API authentication."""
    
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session id={self.id!r} user_id={self.user_id!r}>"

    def is_valid(self) -> bool:
        """Check if session is valid (not expired and not revoked)."""
        return not self.revoked and datetime.utcnow().replace(tzinfo=None) < self.expires_at.replace(tzinfo=None)


class DiscordOAuthPending(Base):
    """Pending Discord OAuth verification (temporary)."""
    
    __tablename__ = "discord_oauth_pending"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    state: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    code_verifier: Mapped[str | None] = mapped_column(String(256), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.utcnow().replace(tzinfo=None) + timedelta(minutes=10)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DiscordOAuthPending id={self.id!r} state={self.state!r}>"
