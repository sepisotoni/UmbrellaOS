"""
models/discord.py — Discord account linking and chat bridge models.

DiscordAccount: Links Discord users to Minecraft players
ChatMessage: Stores chat messages for the MC-Discord bridge
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class DiscordAccount(Base):
    """Links a Discord user account to a Minecraft player."""
    
    __tablename__ = "discord_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    player_uuid: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("players.uuid", ondelete="SET NULL"), nullable=True, index=True
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discord_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    banned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    ban_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    previous_usernames: Mapped[str | None] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return f"<DiscordAccount id={self.id!r} discord_id={self.discord_id!r} player_uuid={self.player_uuid!r}>"


class ChatMessage(Base):
    """Stores chat messages for the Minecraft-Discord bridge."""
    
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # "minecraft" or "discord"
    player_uuid: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("players.uuid", ondelete="SET NULL"), nullable=True, index=True
    )
    discord_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    discord_channel_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    translated_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    filtered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id!r} source={self.source!r} timestamp={self.timestamp!r}>"
