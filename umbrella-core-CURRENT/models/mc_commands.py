"""
models/mc_commands.py — Minecraft command execution model.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class MCCommand(Base):
    """Queued Minecraft commands from Discord."""
    __tablename__ = "mc_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command: Mapped[str] = mapped_column(String(512), nullable=False)
    # FIX ([PLUGIN] subsystem audit, master fleet-awareness gap): previously
    # had no server routing at all. In a single-server deployment this was
    # invisible — there was only one plugin instance to poll and execute
    # everything. In a real fleet (this codebase's Node/Server/daemon system
    # explicitly supports multiple Minecraft servers under one core), EVERY
    # plugin instance polled the exact same global pending-commands queue and
    # executed EVERY command, regardless of which specific server it was
    # meant for — a command targeting "Server A" would also run on B, C, D...
    # Confirmed live: umbrella-dashboard-CURRENT's sendServerCommand(serverId,
    # command) already accepted a serverId parameter but silently dropped it
    # from the request body; the plugin's CommandPoller never sent one either,
    # despite HeartbeatManager already tracking and sending the plugin's own
    # server_id via the exact same config value.
    # default="default" preserves existing single-server-deployment behavior
    # unchanged — anyone not yet passing a real server_id keeps working
    # exactly as before, scoped to one implicit "default" queue.
    server_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", server_default="default", index=True
    )
    requested_by_discord_id: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_username: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<MCCommand id={self.id!r} command={self.command!r} status={self.status!r}>"
