"""Plugin console line buffer — stores recent console output from connected servers."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class PluginConsoleLine(Base):
    __tablename__ = "plugin_console_lines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # CORRECTION ([PLUGIN] subsystem audit): this was previously declared
    # index=False, and my first attempt at fixing it "added" a composite
    # index (server_id, captured_at) via a new migration (051) — before
    # verifying against real Postgres and discovering the model was simply
    # WRONG, not the database. Migration 035_plugin_console_lines.py (the
    # migration that created this table) already creates
    # "ix_plugin_console_lines_server_id_ts" on (server_id, captured_at
    # DESC) — the model's own declaration just never matched it. My first
    # migration created a second, redundant, differently-named, opposite-
    # sort-direction index alongside the real one. Deleted that migration;
    # this __table_args__ now correctly documents the index that has always
    # existed since 035, matching its real name and DESC ordering (which
    # index=True on the column alone can't express) rather than adding
    # anything new to the schema. No new migration needed — nothing to
    # apply, the database has been correct since 035.
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    line: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_plugin_console_lines_server_id_ts", "server_id", captured_at.desc()),
    )
