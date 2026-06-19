"""Plugin heartbeat registry — tracks connected Minecraft servers."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class PluginHeartbeat(Base):
    __tablename__ = "plugin_heartbeats"

    server_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    server_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Minecraft Server")
    online_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tps: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    plugin_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    grim_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
