"""tests/registry/test_plugin_sandbox.py — ProcessSandbox: the real
execution boundary. Every one of these enforces something Moo's
CodeExecutionService explicitly did NOT (see sandbox.py's module
docstring for the side-by-side comparison) — each test name maps directly
to one row of that comparison.
"""
import pytest

from services.plugins.sandbox import (
    ProcessSandbox,
    ResourceLimits,
    SandboxExecutionError,
    SqliteQuotaExceeded,
    SqliteSandboxConnection,
)
from services.plugins.sandbox_guard import SandboxViolation


def _fast_limits(**overrides) -> ResourceLimits:
    defaults = dict(cpu_seconds=2, memory_bytes=64 * 1024 * 1024, wall_timeout_seconds=5)
    defaults.update(overrides)
    return ResourceLimits(**defaults)


@pytest.mark.asyncio
async def test_happy_path_executes_and_returns_result():
    src = "def run(params):\n    return {'doubled': params.get('n', 0) * 2}\n"
    sandbox = ProcessSandbox(sources={"p": {"h": src}}, limits=_fast_limits())
    result = await sandbox.run(plugin_id="p", entrypoint="h:run", params={"n": 21}, actor_id="u1")
    assert result == {"doubled": 42}


@pytest.mark.asyncio
async def test_import_statement_rejected_before_process_spawns():
    """Static guard runs inside run() before any process is spawned —
    this is the 'fail fast, clear error' layer described in
    sandbox_guard.py's docstring."""
    src = "import os\ndef run(params):\n    return {}\n"
    sandbox = ProcessSandbox(sources={"p": {"h": src}}, limits=_fast_limits())
    with pytest.raises(SandboxViolation):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_missing_source_raises_clear_error():
    sandbox = ProcessSandbox(sources={}, limits=_fast_limits())
    with pytest.raises(SandboxExecutionError):
        await sandbox.run(plugin_id="nope", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_missing_entrypoint_function_raises():
    src = "def some_other_name(params):\n    return {}\n"
    sandbox = ProcessSandbox(sources={"p": {"h": src}}, limits=_fast_limits())
    with pytest.raises(SandboxExecutionError, match="run"):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_non_dict_return_value_raises():
    src = "def run(params):\n    return 'not a dict'\n"
    sandbox = ProcessSandbox(sources={"p": {"h": src}}, limits=_fast_limits())
    with pytest.raises(SandboxExecutionError, match="must return a dict"):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_uncaught_plugin_exception_surfaces_as_sandbox_error():
    src = "def run(params):\n    return {'x': 1 / 0}\n"
    sandbox = ProcessSandbox(sources={"p": {"h": src}}, limits=_fast_limits())
    with pytest.raises(SandboxExecutionError, match="ZeroDivisionError"):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_cpu_limit_kills_infinite_loop():
    """Real enforced behavior, not a comment: an infinite loop actually
    gets SIGXCPU'd by RLIMIT_CPU rather than hanging the sandbox forever."""
    src = "def run(params):\n    x = 0\n    while True:\n        x += 1\n"
    sandbox = ProcessSandbox(
        sources={"p": {"h": src}},
        limits=ResourceLimits(cpu_seconds=1, memory_bytes=64 * 1024 * 1024, wall_timeout_seconds=5),
    )
    with pytest.raises(SandboxExecutionError, match="signal|timeout"):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_wall_timeout_kills_process_when_cpu_limit_is_generous():
    """Distinct code path from the CPU-limit test above: a wall-clock
    timeout shorter than the CPU limit must still terminate the process
    (covers hangs that aren't themselves CPU-bound in the general case;
    here the same busy-loop is used only because the sandbox has no
    blocking I/O primitives available to a plugin to construct a
    non-CPU-bound hang with)."""
    src = "def run(params):\n    x = 0\n    while True:\n        x += 1\n"
    sandbox = ProcessSandbox(
        sources={"p": {"h": src}},
        limits=ResourceLimits(cpu_seconds=100, memory_bytes=64 * 1024 * 1024, wall_timeout_seconds=1),
    )
    with pytest.raises(SandboxExecutionError, match="timeout"):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_memory_limit_kills_oversized_allocation():
    src = "def run(params):\n    big = 'x' * (200 * 1024 * 1024)\n    return {'len': len(big)}\n"
    sandbox = ProcessSandbox(
        sources={"p": {"h": src}},
        limits=ResourceLimits(cpu_seconds=5, memory_bytes=64 * 1024 * 1024, wall_timeout_seconds=8),
    )
    with pytest.raises(SandboxExecutionError, match="MemoryError"):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")


@pytest.mark.asyncio
async def test_safe_modules_are_usable_without_import():
    """json/math/re/datetime/collections are pre-bound globals — a plugin
    can use them productively despite import statements being forbidden."""
    src = (
        "def run(params):\n"
        "    payload = json.dumps({'a': 1})\n"
        "    root = math.sqrt(16)\n"
        "    matched = bool(re.match(r'^ab', 'abc'))\n"
        "    counted = collections.Counter('aab')\n"
        "    return {'payload': payload, 'root': root, 'matched': matched, 'a_count': counted['a']}\n"
    )
    sandbox = ProcessSandbox(sources={"p": {"h": src}}, limits=_fast_limits())
    result = await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")
    assert result == {"payload": '{"a": 1}', "root": 4.0, "matched": True, "a_count": 2}


def test_restricted_builtins_omit_dangerous_names_directly():
    """Independent, second-layer check of the runtime globals themselves
    (not routed through the static guard, which already forbids
    referencing these names in plugin source at all) — asserts the
    restricted-builtins dict genuinely doesn't contain them, rather than
    only trusting the static guard to keep a plugin from reaching them."""
    from services.plugins.sandbox import _build_safe_globals

    g = _build_safe_globals()
    dangerous = {"open", "eval", "exec", "compile", "__import__", "input", "exit", "quit"}
    present = dangerous & set(g["__builtins__"].keys())
    assert present == set(), f"dangerous builtins leaked into sandbox globals: {present}"


@pytest.mark.asyncio
async def test_set_plugin_sources_makes_plugin_callable():
    sandbox = ProcessSandbox(sources={})
    sandbox.set_plugin_sources("demo-plugin", {"handlers": "def run(params):\n    return {'ok': True}\n"})
    result = await sandbox.run(plugin_id="demo-plugin", entrypoint="handlers:run", params={}, actor_id="u1")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_remove_plugin_sources_makes_plugin_uncallable():
    sandbox = ProcessSandbox(sources={"demo-plugin": {"handlers": "def run(params):\n    return {}\n"}})
    sandbox.remove_plugin_sources("demo-plugin")
    with pytest.raises(SandboxExecutionError):
        await sandbox.run(plugin_id="demo-plugin", entrypoint="handlers:run", params={}, actor_id="u1")


def test_remove_plugin_sources_is_a_noop_for_unknown_plugin():
    sandbox = ProcessSandbox(sources={})
    sandbox.remove_plugin_sources("never-installed")  # must not raise


def test_set_plugin_sources_replaces_previous_version_wholesale():
    """Updating a plugin replaces its entire module map, not a merge —
    a module removed in the new version must not still be callable."""
    sandbox = ProcessSandbox(sources={})
    sandbox.set_plugin_sources("demo-plugin", {"old_module": "def run(params):\n    return {}\n"})
    sandbox.set_plugin_sources("demo-plugin", {"new_module": "def run(params):\n    return {}\n"})
    assert "old_module" not in sandbox._sources["demo-plugin"]
    assert "new_module" in sandbox._sources["demo-plugin"]


def test_sqlite_quota_enforced(tmp_path):
    db_path = str(tmp_path / "plugin.db")
    conn = SqliteSandboxConnection(db_path, quota_bytes=64 * 1024)  # tiny quota
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.commit()
    with pytest.raises(SqliteQuotaExceeded):
        for _ in range(2000):
            conn.execute("INSERT INTO t (v) VALUES (?)", ("x" * 200,))
            conn.commit()
    conn.close()


def test_sqlite_quota_allows_writes_under_quota(tmp_path):
    db_path = str(tmp_path / "plugin.db")
    conn = SqliteSandboxConnection(db_path, quota_bytes=10 * 1024 * 1024)
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.execute("INSERT INTO t (v) VALUES (?)", ("hello",))
    conn.commit()
    row = conn.execute("SELECT v FROM t").fetchone()
    assert row == ("hello",)
    conn.close()


# --- Phase 9: sandbox violations are observable, not just rejected ---


@pytest.mark.asyncio
async def test_static_guard_rejection_increments_sandbox_violations_metric():
    from services.metrics_service import sandbox_violations_total

    before = dict(sandbox_violations_total._values)
    src = "import os\ndef run(params):\n    return {}\n"
    sandbox = ProcessSandbox(sources={"p": {"h": src}}, limits=_fast_limits())
    with pytest.raises(SandboxViolation):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")
    after = dict(sandbox_violations_total._values)
    assert after.get(("static_guard_rejection",), 0) > before.get(("static_guard_rejection",), 0)


@pytest.mark.asyncio
async def test_resource_limit_kill_increments_sandbox_violations_metric():
    from services.metrics_service import sandbox_violations_total

    before = dict(sandbox_violations_total._values)
    src = "def run(params):\n    x = 0\n    while True:\n        x += 1\n"
    sandbox = ProcessSandbox(
        sources={"p": {"h": src}},
        limits=ResourceLimits(cpu_seconds=1, memory_bytes=64 * 1024 * 1024, wall_timeout_seconds=5),
    )
    with pytest.raises(SandboxExecutionError):
        await sandbox.run(plugin_id="p", entrypoint="h:run", params={}, actor_id="u1")
    after = dict(sandbox_violations_total._values)
    assert after.get(("resource_limit_kill",), 0) > before.get(("resource_limit_kill",), 0)
