"""
tests/test_log_aggregation.py — Tests for services/log_aggregation_service.py
(Phase 9, item 3). See tests/test_threat_detection.py's module docstring
for why AsyncSessionLocal is monkeypatched to the per-test session factory.
"""
import asyncio
import logging

import pytest
from sqlalchemy import select

import services.log_aggregation_service as log_aggregation_service
from models.log_entry import LogEntry


@pytest.fixture(autouse=True)
def _fresh_queue():
    """The module-level queue is process-wide; give each test its own so
    one test's leftover records can't leak into another's assertions."""
    log_aggregation_service._log_queue = None
    yield
    log_aggregation_service._log_queue = None


def test_db_log_handler_enqueues_formatted_record():
    handler = log_aggregation_service.DBLogHandler()
    record = logging.LogRecord(
        name="umbrella.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    handler.emit(record)

    queue = log_aggregation_service.get_log_queue()
    entry = queue.get_nowait()
    assert entry["level"] == "INFO"
    assert entry["logger_name"] == "umbrella.test"
    assert entry["message"] == "hello world"


def test_db_log_handler_excludes_its_own_module_to_avoid_recursion():
    handler = log_aggregation_service.DBLogHandler()
    record = logging.LogRecord(
        name="services.log_aggregation_service", level=logging.ERROR, pathname=__file__,
        lineno=1, msg="a flush error", args=None, exc_info=None,
    )
    handler.emit(record)
    assert log_aggregation_service.get_log_queue().empty()


def test_db_log_handler_never_raises_on_full_queue():
    log_aggregation_service._log_queue = asyncio.Queue(maxsize=1)
    handler = log_aggregation_service.DBLogHandler()
    for _ in range(5):
        record = logging.LogRecord(
            name="umbrella.test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="x", args=None, exc_info=None,
        )
        handler.emit(record)  # must not raise even once the queue is full


@pytest.mark.asyncio
async def test_flush_pending_writes_queued_records_to_db(db_session, monkeypatch):
    monkeypatch.setattr(log_aggregation_service, "AsyncSessionLocal", db_session)
    queue = log_aggregation_service.get_log_queue()
    queue.put_nowait({"level": "WARNING", "logger_name": "umbrella.x", "message": "careful", "trace_id": None})

    async with db_session() as db:
        flushed = await log_aggregation_service.flush_pending(db)
        assert flushed == 1
        rows = (await db.execute(select(LogEntry))).scalars().all()
    assert len(rows) == 1
    assert rows[0].message == "careful"
    assert rows[0].source == "umbrella-core"


@pytest.mark.asyncio
async def test_flush_pending_returns_zero_when_queue_empty(db_session, monkeypatch):
    monkeypatch.setattr(log_aggregation_service, "AsyncSessionLocal", db_session)
    async with db_session() as db:
        flushed = await log_aggregation_service.flush_pending(db)
    assert flushed == 0


@pytest.mark.asyncio
async def test_search_filters_by_query_and_level(db_session, monkeypatch):
    monkeypatch.setattr(log_aggregation_service, "AsyncSessionLocal", db_session)
    async with db_session() as db:
        db.add(LogEntry(level="ERROR", logger_name="umbrella.a", message="disk full", source="umbrella-core"))
        db.add(LogEntry(level="INFO", logger_name="umbrella.b", message="startup complete", source="umbrella-core"))
        await db.commit()

        results = await log_aggregation_service.search(db, query="disk")
        assert len(results) == 1
        assert results[0].message == "disk full"

        results = await log_aggregation_service.search(db, level="INFO")
        assert len(results) == 1
        assert results[0].logger_name == "umbrella.b"


@pytest.mark.asyncio
async def test_search_filters_by_trace_id(db_session, monkeypatch):
    monkeypatch.setattr(log_aggregation_service, "AsyncSessionLocal", db_session)
    async with db_session() as db:
        db.add(LogEntry(level="INFO", logger_name="umbrella.a", message="m1", source="umbrella-core", trace_id="abc123"))
        db.add(LogEntry(level="INFO", logger_name="umbrella.a", message="m2", source="umbrella-core", trace_id="def456"))
        await db.commit()

        results = await log_aggregation_service.search(db, trace_id="abc123")
        assert len(results) == 1
        assert results[0].message == "m1"


@pytest.mark.asyncio
async def test_run_log_flush_loop_stops_promptly_when_signaled(db_session, monkeypatch):
    monkeypatch.setattr(log_aggregation_service, "AsyncSessionLocal", db_session)
    stop_event = asyncio.Event()
    task = asyncio.create_task(log_aggregation_service.run_log_flush_loop(stop_event, interval_seconds=60))
    await asyncio.sleep(0.05)
    stop_event.set()
    await asyncio.wait_for(task, timeout=2.0)
    assert task.done()
