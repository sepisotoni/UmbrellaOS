"""
models/log_entry.py — Aggregated log record (Phase 9, item 3: "Log
aggregation + full-text search across core/daemon/server logs — one
searchable index, not a per-subsystem grep").

Scope note (stated plainly, same as the Phase 7→8 Discord/dashboard loose
end): this table only ever receives records from *this* process
(umbrella-core), via services/log_aggregation_service.py's logging.Handler
attached to the root logger. umbrella-daemon and per-server Minecraft logs
are separate processes this code source has no reach into — genuinely
"one searchable index" across all three would need each of those to ship
its records here (or to a shared sink), which is out-of-repo work, not
forgotten.

Search is plain SQL LIKE/ILIKE (via `.ilike()`, which SQLAlchemy compiles
portably for both SQLite and Postgres) rather than a dedicated full-text
index (SQLite FTS5 virtual tables, Postgres tsvector): the two backends
this project actually runs on need genuinely different DDL for a real FTS
index, and this project's SQLite-over-managed-DB, single-node scale
doesn't need FTS-level relevance ranking to be useful — a substring search
over a properly indexed, timestamp-bounded table is fast enough at this
scale. If log volume ever makes LIKE-scans too slow, swapping the query
side of log_aggregation_service.search() for a real FTS index is a
contained change; nothing else references how search is implemented.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # DEBUG/INFO/WARNING/ERROR/CRITICAL
    logger_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="umbrella-core", index=True)
    trace_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<LogEntry level={self.level!r} logger={self.logger_name!r}>"
