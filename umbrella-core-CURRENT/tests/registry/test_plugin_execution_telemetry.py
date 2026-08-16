"""
tests/registry/test_plugin_execution_telemetry.py — Phase 8 completion,
Task A: exercises ProcessSandbox.run()'s actual PluginExecutionRecord
writes end to end (real forked subprocess, real getrusage() telemetry,
real DB row), not just the pre-existing execution-semantics tests in
test_plugin_sandbox.py (which never touch a database at all).

Follows tests/test_threat_detection.py's exact pattern for testing
AsyncSessionLocal-based service writes: monkeypatch the *module's* bound
name (`services.plugins.sandbox.AsyncSessionLocal`) to the per-test
isolated engine from tests/conftest.py's `db_session` fixture, rather than
touching the real database/engine.py singleton.
"""
import pytest
from sqlalchemy import select

from models.plugin_execution import PluginExecutionRecord
from services.plugins.sandbox import ProcessSandbox, ResourceLimits, SandboxExecutionError

OK_SOURCE = """
def handle(params):
    return {"ok": True, "echo": params.get("value")}
"""

RAISES_SOURCE = """
def handle(params):
    raise ValueError("boom")
"""

BUSY_LOOP_SOURCE = """
def handle(params):
    x = 0
    while True:
        x += 1
"""


@pytest.fixture
def _patched_session(db_session, monkeypatch):
    import services.plugins.sandbox as sandbox_module

    monkeypatch.setattr(sandbox_module, "AsyncSessionLocal", db_session)
    return db_session


async def _all_records(db_session) -> list[PluginExecutionRecord]:
    async with db_session() as db:
        rows = (await db.execute(select(PluginExecutionRecord))).scalars().all()
    return rows


@pytest.mark.asyncio
async def test_successful_execution_writes_a_record_with_real_telemetry(_patched_session, db_session):
    sandbox = ProcessSandbox({"demo-plugin": {"main": OK_SOURCE}})

    result = await sandbox.run(
        plugin_id="demo-plugin", entrypoint="main:handle", params={"value": 42}, actor_id="user-1"
    )
    assert result == {"ok": True, "echo": 42}

    rows = await _all_records(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.plugin_id == "demo-plugin"
    assert row.entrypoint == "main:handle"
    assert row.actor_id == "user-1"
    assert row.outcome == "success"
    assert row.error_detail is None

    # Real, not fabricated: wall time was actually measured by run() around
    # a real subprocess fork/join, so it must be positive but bounded (this
    # trivial handler shouldn't take more than a couple of seconds even on
    # a slow CI box).
    assert 0 < row.wall_time_ms < 5000

    # Real getrusage() values from inside the child, per this module's own
    # documented approach (_self_rusage_telemetry) — not just "some
    # non-null number": cpu_time_ms must be non-negative and small for a
    # trivial handler, and peak_memory_bytes must be a plausible resident
    # size for a freshly-forked Python interpreter (a few MB at minimum,
    # nowhere near the sandbox's configured ceiling).
    assert row.cpu_time_ms is not None
    assert row.cpu_time_ms >= 0
    assert row.cpu_time_ms < 5000
    assert row.peak_memory_bytes is not None
    assert 1_000_000 < row.peak_memory_bytes < 500_000_000


@pytest.mark.asyncio
async def test_uncaught_exception_writes_an_error_record_with_telemetry_and_detail(_patched_session, db_session):
    sandbox = ProcessSandbox({"demo-plugin": {"main": RAISES_SOURCE}})

    with pytest.raises(SandboxExecutionError):
        await sandbox.run(plugin_id="demo-plugin", entrypoint="main:handle", params={}, actor_id="user-1")

    rows = await _all_records(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.outcome == "error"
    assert row.error_detail is not None
    assert "ValueError" in row.error_detail
    assert "boom" in row.error_detail
    # The child got far enough to raise and self-report — telemetry
    # should still be populated for a genuine uncaught exception (as
    # opposed to a signal-kill, covered below).
    assert row.cpu_time_ms is not None
    assert row.peak_memory_bytes is not None


@pytest.mark.asyncio
async def test_resource_limit_kill_writes_a_record_with_null_telemetry(_patched_session, db_session):
    """A CPU-limit kill (RLIMIT_CPU -> SIGXCPU) terminates the child before
    it ever reaches _self_rusage_telemetry() — per this module's own
    documented, deliberate nullability, the record must still be written,
    just with cpu_time_ms/peak_memory_bytes left null rather than guessed."""
    limits = ResourceLimits(cpu_seconds=1, memory_bytes=256 * 1024 * 1024, wall_timeout_seconds=10)
    sandbox = ProcessSandbox({"demo-plugin": {"main": BUSY_LOOP_SOURCE}}, limits=limits)

    with pytest.raises(SandboxExecutionError):
        await sandbox.run(plugin_id="demo-plugin", entrypoint="main:handle", params={}, actor_id="user-1")

    rows = await _all_records(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.outcome == "resource_limit_kill"
    assert row.cpu_time_ms is None
    assert row.peak_memory_bytes is None
    assert row.wall_time_ms > 0


@pytest.mark.asyncio
async def test_static_guard_rejection_writes_no_execution_record(_patched_session, db_session):
    """A static-guard rejection never spawns a process — per this module's
    own comment on that branch, it's deliberately not a
    PluginExecutionRecord (threat_detection_service already gives it its
    own trail; a record with every telemetry field null would be noise,
    not signal)."""
    disallowed_source = "import os\ndef handle(params):\n    return {}\n"
    sandbox = ProcessSandbox({"demo-plugin": {"main": disallowed_source}})

    with pytest.raises(Exception):
        await sandbox.run(plugin_id="demo-plugin", entrypoint="main:handle", params={}, actor_id="user-1")

    rows = await _all_records(db_session)
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_telemetry_write_failure_does_not_break_the_capability_call(monkeypatch):
    """Fail-open, mirroring test_threat_detection.py's
    test_record_never_raises_when_db_unavailable: a broken telemetry
    session factory must not turn into a broken (successful) plugin call —
    same "observability path must not break the thing it's observing"
    principle documented on _record_execution itself."""
    import services.plugins.sandbox as sandbox_module

    class _BrokenSessionLocal:
        def __call__(self):
            raise RuntimeError("db is down")

    monkeypatch.setattr(sandbox_module, "AsyncSessionLocal", _BrokenSessionLocal())

    sandbox = ProcessSandbox({"demo-plugin": {"main": OK_SOURCE}})
    result = await sandbox.run(
        plugin_id="demo-plugin", entrypoint="main:handle", params={"value": 1}, actor_id="user-1"
    )
    assert result == {"ok": True, "echo": 1}
