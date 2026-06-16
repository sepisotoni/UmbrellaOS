"""
models/setting.py — Key-value settings registry.

Design decisions:
- Settings live in the database (not .env) after first boot,
  so they can be edited from the dashboard without restarting Core.
- sensitive=True masks the value in API responses.
- requires_restart=True tells the dashboard to show a warning banner.
- category groups related settings for the UI (e.g. "discord", "rcon").
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from database.engine import Base


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_restart: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Setting key={self.key!r} category={self.category!r}>"
