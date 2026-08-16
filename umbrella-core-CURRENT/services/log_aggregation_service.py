"""
services/log_aggregation_service.py — Aggregates this process's log
records into `log_entries` (models/log_entry.py) and provides search over
them (Phase 9, item 3). See models/log_entry.py's docstring for the scope
and search-implementation notes.

Design: `DBLogHandler` is a stdlib `logging.Handler` attached to the root
logger. Handlers run synchronously, inline in whatever code called
`logger.info(...)` — they cannot `await` a DB write without turning every
logging call site into an async one, which nothing in this codebase does
today. So the handler only ever puts a plain dict onto a bounded
`asyncio.Queue` (non-blocking `put_nowait`, and — deliberately — DROPS the
record rather than blocking or raising if the queue is full; a logging
subsystem back-pressuring or crashing the app it's supposed to be
observing would be strictly worse than losing a burst of low-priority log
lines). `run_log_flush_loop()` is the actual async consumer, wired into
main.py's lifespan with the same stop_event pattern as the scheduler,
sampler, and event-dispatcher loops already there.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.log_entry import LogEntry
from services.tracing_service import current_trace_id

logger = logging.getLogger(__name__)

# Bounded so a logging storm can't grow unbounded memory; records beyond
# this are dropped (see module docstring) rather than applying back-pressure.
_QUEUE_MAXSIZE = 5000
_log_queue: asyncio.Queue | None = None

# Never re-aggregate our own aggregation machinery's logs — a DB error
# while flushing would otherwise re-enter this same logger and loop.
_EXCLUDED_LOGGERS = {__name__}


def get_log_queue() -> asyncio.Queue:
    global _log_queue
    if _log_queue is None:
        _log_queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
    return _log_queue


class DBLogHandler(logging.Handler):
    """Attach to the root logger. Never raises — logging.Handler's
    contract is that a handler failure must not break the log call site,
    enforced here explicitly rather than relying on logging's own default
    error-swallowing (which also silently disables the handler after
    enough consecutive errors)."""

    def emit(self, record: logging.LogRecord) -> None:
        if record.name in _EXCLUDED_LOGGERS:
            return
        try:
            queue = get_log_queue()
            entry = {
                "level": record.levelname,
                "logger_name": record.name,
                "message": self.format(record),
                "trace_id": current_trace_id(),
            }
            queue.put_nowait(entry)
        except asyncio.QueueFull:
            pass
        except Exception:
            pass


async def flush_pending(db: AsyncSession, *, max_batch: int = 200) -> int:
    """Drains up to `max_batch` queued records into the DB in one
    transaction. Returns the number flushed. Exposed separately from the
    loop below so tests can flush deterministically instead of racing a
    background task."""
    queue = get_log_queue()
    flushed = 0
    while flushed < max_batch:
        try:
            entry = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        db.add(LogEntry(source="umbrella-core", **entry))
        flushed += 1
    if flushed:
        await db.commit()
    return flushed


async def run_log_flush_loop(stop_event: asyncio.Event, *, interval_seconds: float = 2.0) -> None:
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                await flush_pending(db)
        except Exception:
            logger.exception("log flush loop: error flushing queued log records, will retry next interval")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue

    # Final drain on shutdown so in-flight records aren't silently lost.
    try:
        async with AsyncSessionLocal() as db:
            await flush_pending(db, max_batch=_QUEUE_MAXSIZE)
    except Exception:
        logger.exception("log flush loop: error during final shutdown flush")


async def search(
    db: AsyncSession,
    *,
    query: str | None = None,
    level: str | None = None,
    source: str | None = None,
    trace_id: str | None = None,
    limit: int = 50,
) -> list[LogEntry]:
    """Portable substring search (see models/log_entry.py docstring for
    why this isn't a dedicated FTS index)."""
    stmt = select(LogEntry).order_by(LogEntry.created_at.desc()).limit(min(limit, 500))
    if query:
        stmt = stmt.where(or_(LogEntry.message.ilike(f"%{query}%"), LogEntry.logger_name.ilike(f"%{query}%")))
    if level:
        stmt = stmt.where(LogEntry.level == level.upper())
    if source:
        stmt = stmt.where(LogEntry.source == source)
    if trace_id:
        stmt = stmt.where(LogEntry.trace_id == trace_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
