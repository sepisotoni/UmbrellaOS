"""Plugin console line buffer — stores recent console output from connected servers."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class PluginConsoleLine(Base):
    __tablename__ = "plugin_console_lines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # FIX ([PLUGIN] subsystem audit): server_id was explicitly index=False
    # despite every single query against this table (push_console_lines'
    # trim-to-cap lookup, get_recent_console, the row-count check) filtering
    # WHERE server_id == ... combined with ORDER BY captured_at. A composite
    # index on (server_id, captured_at) serves all three of those query
    # shapes directly — the leading column covers the equality filter, the
    # second covers the ORDER BY/range within that filtered set — rather
    # than a single-column index on server_id alone, which would still leave
    # a separate sort step for every query here.
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    line: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_plugin_console_lines_server_id_captured_at", "server_id", "captured_at"),
    )
