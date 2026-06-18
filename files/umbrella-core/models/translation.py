"""
models/translation.py — Player language preferences for translation.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class PlayerLanguage(Base):
    """Player language preferences for translation."""
    __tablename__ = "player_languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    language_code: Mapped[str] = mapped_column(
        String(8), nullable=False, default="en", server_default="en"
    )
    language_name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="English", server_default="English"
    )
    auto_translate_incoming: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    auto_translate_outgoing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<PlayerLanguage player_uuid={self.player_uuid!r} language={self.language_code!r}>"
