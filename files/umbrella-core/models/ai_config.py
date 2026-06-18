"""
models/ai_config.py — AI configuration actions model.

Stores AI-generated configuration suggestions and their approval status.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class AIConfigAction(Base):
    """AI-generated configuration suggestions."""
    __tablename__ = "ai_config_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # dashboard_layout, discord_config, plugin_config
    natural_language_input: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # what the user typed
    ai_interpretation: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # what AI understood
    proposed_changes: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON string of changes to make
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending"
    )  # pending/approved/rejected/applied
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AIConfigAction id={self.id!r} action_type={self.action_type!r} status={self.status!r}>"
