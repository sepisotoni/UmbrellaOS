"""
models/player.py — Player, IP tracking, punishments, and appeals.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class Player(Base):
    __tablename__ = "players"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    playtime: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    joins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    deaths: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    discord_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ip_addresses: Mapped[list["IPAddress"]] = relationship(
        "IPAddress", back_populates="player", cascade="all, delete-orphan"
    )
    punishments: Mapped[list["Punishment"]] = relationship(
        "Punishment", back_populates="player", cascade="all, delete-orphan"
    )
    appeals: Mapped[list["Appeal"]] = relationship(
        "Appeal", back_populates="player", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Player uuid={self.uuid!r} username={self.username!r}>"


class IPAddress(Base):
    __tablename__ = "ip_addresses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    player_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("players.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    player: Mapped["Player"] = relationship("Player", back_populates="ip_addresses")

    def __repr__(self) -> str:
        return f"<IPAddress ip={self.ip_address!r} player_uuid={self.player_uuid!r}>"


class Punishment(Base):
    __tablename__ = "punishments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    player_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("players.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    staff_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    player: Mapped["Player"] = relationship("Player", back_populates="punishments")
    appeals: Mapped[list["Appeal"]] = relationship(
        "Appeal", back_populates="punishment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Punishment id={self.id!r} type={self.type!r} player_uuid={self.player_uuid!r}>"


class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    punishment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("punishments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("players.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    punishment: Mapped["Punishment"] = relationship("Punishment", back_populates="appeals")
    player: Mapped["Player"] = relationship("Player", back_populates="appeals")

    def __repr__(self) -> str:
        return f"<Appeal id={self.id!r} status={self.status!r} player_uuid={self.player_uuid!r}>"
