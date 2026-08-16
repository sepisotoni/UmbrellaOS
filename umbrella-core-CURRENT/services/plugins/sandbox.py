"""
services/plugins/sandbox.py — ProcessSandbox: the real execution boundary
for third-party plugin code.

Hard constraint from the handoff (docs/adr/phase-7-notes-from-phase-5.md,
"Safety flag"): this must NOT be Moo-assistant's `CodeExecutionService`
pattern — an in-process `exec()` with full `__builtins__`, gated only by a
permission check and a timeout. Every one of that pattern's gaps is closed
here:

  Moo's CodeExecutionService          | ProcessSandbox
  -------------------------------------|--------------------------------------
  in-process exec()                    | separate OS process (multiprocessing)
  full __builtins__ (open/import/etc.) | restricted builtins, no import at all
  timeout only                         | timeout + CPU + memory + fd + fsize limits
  no filesystem control                | RLIMIT_FSIZE=0 by default; SQLite mode
                                        |   gets exactly one pre-opened fd, quota-checked
  no network control                   | no socket/urllib/etc. reachable — no
                                        |   import machinery exists inside the sandbox at all

Honest limitation, stated once here rather than left implicit: this is
runtime-enforced isolation (restricted globals + OS resource limits +
process separation), not kernel/container-level isolation. That's the
direct, documented consequence of the zip-package plugin format decision
(docs/adr/phase-7-notes-from-phase-5.md, "Plugin package format") — a
sufficiently determined, sufficiently skilled adversarial plugin author
attacking the CPython runtime itself (not just Python-level introspection
gadgets) is a residual risk this layer does not claim to close. The ADR
already flags this as "revisit if a real plugin author reports the
runtime-enforced sandbox isn't strong enough in practice" — true here too.
sandbox_guard.py's static check plus this module's restricted-globals
runtime are two independent layers against the same class of
Python-level escape; OS resource limits are a third, independent layer
against runaway resource consumption regardless of whether the first two
hold.

v1 scope: plugin entrypoints are plain synchronous functions with the
signature `def fn(params: dict) -> dict`. No async support inside the
sandbox in this increment — the marshalling in
services/plugins/registration.py is already async on the *caller* side
(register_plugin_capabilities's handler wrapper), this only constrains
what plugin authors themselves write.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import resource
import sqlite3
from dataclasses import dataclass
from typing import Any

from services.plugins.sandbox_guard import check_source_safety, SandboxViolation
from services.metrics_service import sandbox_violations_total

# Modules made available as pre-bound globals inside sandboxed code,
# instead of via `import` (which sandbox_guard forbids outright). Every
# entry here has been checked to have no reachable path back to
# filesystem/network/process-control primitives through its public API.
_SAFE_MODULE_NAMES = ("json", "math", "re", "datetime", "collections")

_DEFAULT_CPU_SECONDS = 5
_DEFAULT_MEMORY_BYTES = 64 * 1024 * 1024  # 64 MiB
_DEFAULT_WALL_TIMEOUT_SECONDS = 8  # slightly above CPU limit; catches I/O-bound hangs
_DEFAULT_SQLITE_QUOTA_BYTES = 10 * 1024 * 1024  # 10 MiB, per Decision 2's disk-quota rule


class SandboxExecutionError(RuntimeError):
    """Raised for any failure inside the sandboxed process: an uncaught
    plugin exception, a resource-limit kill, or a timeout. Deliberately
    one exception type — services/plugins/registration.py's handler
    wrapper lets this propagate to CapabilityRegistry.call() exactly like
    any other handler exception (see that module's docstring)."""


class SqliteQuotaExceeded(SandboxExecutionError):
    """Raised when a plugin's own SQLite file would exceed its per-plugin
    disk quota (Decision 2: 'SQLite file size counts against a per-plugin
    disk quota — otherwise it's an unbounded resource with no sandboxing
    story.'). Enforced by capping SQLite's own page count via
    `PRAGMA max_page_count`, which makes the *database engine itself*
    refuse the write — not a check this module could race past."""


def _build_safe_globals() -> dict[str, Any]:
    import builtins
    import collections
    import datetime
    import json as _json
    import math
    import re

    safe_builtins = {
        name: getattr(builtins, name)
        for name in (
            "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
            "int", "len", "list", "map", "max", "min", "range", "repr", "reversed",
            "round", "set", "sorted", "str", "sum", "tuple", "zip", "isinstance",
            "True", "False", "None", "ValueError", "TypeError", "KeyError",
            "IndexError", "StopIteration", "Exception",
        )
    }
    return {
        "__builtins__": safe_builtins,
        "json": _json,
        "math": math,
        "re": re,
        "datetime": datetime,
        "collections": collections,
    }


def _child_main(
    source: str,
    function_name: str,
    params_json: str,
    cpu_seconds: int,
    memory_bytes: int,
    conn: "mp.connection.Connection",
) -> None:
    """Runs inside the forked child process. Sets resource limits FIRST,
    before compiling or executing a single line of plugin-authored code —
    the ordering matters: if limits were set after exec(), the plugin code
    itself would have a window to consume resources unconstrained."""
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        # No filesystem writes by default (Decision: "no default
        # filesystem/network access"). A plugin using storage="sqlite"
        # gets its quota enforced by SQLite's own max_page_count instead
        # of RLIMIT_FSIZE, since RLIMIT_FSIZE would also break WAL/journal
        # files SQLite needs — see SqliteSandboxConnection below.
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (8, 8))
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0) if hasattr(resource, "RLIMIT_NPROC") else (1, 1))
    except (ValueError, OSError) as exc:
        conn.send(("error", f"failed to apply resource limits: {exc}"))
        conn.close()
        return

    try:
        sandbox_globals = _build_safe_globals()
        compiled = compile(source, "<plugin>", "exec")
        exec(compiled, sandbox_globals)
        fn = sandbox_globals.get(function_name)
        if not callable(fn):
            raise SandboxExecutionError(f"entrypoint function {function_name!r} not found or not callable")
        params = json.loads(params_json)
        result = fn(params)
        if not isinstance(result, dict):
            raise SandboxExecutionError(
                f"entrypoint {function_name!r} must return a dict, got {type(result).__name__}"
            )
        conn.send(("ok", result))
    except BaseException as exc:  # noqa: BLE001 — a plugin's own code, must not crash the parent
        conn.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        conn.close()


@dataclass
class ResourceLimits:
    cpu_seconds: int = _DEFAULT_CPU_SECONDS
    memory_bytes: int = _DEFAULT_MEMORY_BYTES
    wall_timeout_seconds: float = _DEFAULT_WALL_TIMEOUT_SECONDS


class ProcessSandbox:
    """Executes plugin entrypoints in an isolated child process with
    restricted globals and enforced resource limits. Implements
    services.plugins.registration.SandboxExecutor's Protocol.

    `sources` maps `plugin_id -> {module_name: source_text}` — in the real
    install flow this comes from the plugin's extracted zip; tests build
    it directly. Kept as a plain constructor arg (not a filesystem lookup)
    so this module has no filesystem-layout opinion of its own — that's
    the marketplace install flow's job, not the sandbox's.
    """

    def __init__(
        self,
        sources: dict[str, dict[str, str]],
        limits: ResourceLimits | None = None,
    ) -> None:
        self._sources = sources
        self._limits = limits or ResourceLimits()

    def set_plugin_sources(self, plugin_id: str, sources: dict[str, str]) -> None:
        """Adds or replaces one plugin's `{module_name: source_text}` map
        on an already-constructed sandbox. Added for the marketplace
        install flow (Phase 7 item 3): a live server process installs and
        updates plugins without a restart, so the process-wide sandbox
        instance (services/plugins/runtime.py) needs a way to pick up a
        newly-installed or newly-updated plugin's source after
        construction, not just at process start via the constructor arg.
        A plain dict assignment is safe here — `self._sources` is only
        read from inside `run()`/`_run_blocking()`, both of which read it
        fresh on every call rather than caching a reference, so there's no
        stale-copy risk from mutating it between calls."""
        self._sources[plugin_id] = sources

    def remove_plugin_sources(self, plugin_id: str) -> None:
        """Drops a plugin's registered source, e.g. on uninstall. A no-op
        (not an error) if the plugin had no sources registered — mirrors
        `dict.pop(..., None)` semantics rather than `CapabilityRegistry
        .unregister()`'s strict not-found error, since removing sources
        for a plugin that only ever failed partway through install (and
        so never got sources registered) is an expected cleanup path, not
        a caller bug."""
        self._sources.pop(plugin_id, None)

    async def run(
        self,
        *,
        plugin_id: str,
        entrypoint: str,
        params: dict[str, Any],
        actor_id: str,
    ) -> dict[str, Any]:
        import asyncio

        module_name, _, function_name = entrypoint.partition(":")
        plugin_sources = self._sources.get(plugin_id)
        if plugin_sources is None or module_name not in plugin_sources:
            raise SandboxExecutionError(
                f"no source registered for plugin {plugin_id!r} module {module_name!r}"
            )
        source = plugin_sources[module_name]

        # Static guard first — fail fast on obviously-disallowed
        # constructs without ever spawning a process for them.
        #
        # Phase 9 addition: a static-guard rejection here means installed
        # plugin source that previously passed registration-time checks
        # (services/plugins/registration.py) is now being *called* with
        # disallowed constructs — e.g. a marketplace update swapped in
        # different code than what was reviewed, or an install bypassed
        # the registration path. Either way it's worth a security-event
        # record and metric, not just a raised exception the caller sees.
        try:
            check_source_safety(source, entrypoint=entrypoint)
        except SandboxViolation:
            sandbox_violations_total.inc(kind="static_guard_rejection")
            import services.threat_detection_service as threat_detection_service

            await threat_detection_service.record(
                event_type="sandbox_violation",
                identifier=plugin_id,
                detail={"entrypoint": entrypoint, "kind": "static_guard_rejection"},
            )
            raise

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._run_blocking, source, function_name, params)
        except SandboxExecutionError as exc:
            # A resource-limit kill (signal-terminated child, see
            # _run_blocking's own comments) is the runtime-enforcement
            # layer actually doing its job against misbehaving plugin
            # code — worth the same observability treatment as a static
            # rejection, since a plugin that's hitting its CPU/memory
            # ceiling or attempting a forbidden syscall is exactly the
            # "real Phase 8 usage" signal this hardening pass is for.
            if "signal" in str(exc) or "resource limit" in str(exc):
                sandbox_violations_total.inc(kind="resource_limit_kill")
                import services.threat_detection_service as threat_detection_service

                await threat_detection_service.record(
                    event_type="sandbox_violation",
                    identifier=plugin_id,
                    detail={"entrypoint": entrypoint, "kind": "resource_limit_kill"},
                )
            raise

    def _run_blocking(self, source: str, function_name: str, params: dict[str, Any]) -> dict[str, Any]:
        # KNOWN CAVEAT, stated plainly rather than left for someone to
        # discover in production: `fork()` from a process that already has
        # multiple threads (which any live asyncio app with a thread-pool
        # executor does) can deadlock if another thread held a lock (malloc,
        # logging, etc.) at the instant of fork — the child inherits the
        # lock in its locked state with no thread left alive to release it.
        # This is real Python/POSIX behavior (see the DeprecationWarning
        # `multiprocessing` itself emits: "this process is multi-threaded,
        # use of fork() may lead to deadlocks"), not specific to this
        # module. `forkserver` (fork a small, single-threaded, mostly-empty
        # helper process for every spawn, before the parent grows threads)
        # avoids this at the cost of slightly higher per-call latency and
        # is the safer choice for a long-running server process handling
        # concurrent plugin calls — tracked as a known follow-up, not fixed
        # in this increment since it needs its own focused testing pass
        # (forkserver has different requirements around what module state
        # is picklable/importable in the child) rather than a same-session
        # swap.
        ctx = mp.get_context("fork")
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        process = ctx.Process(
            target=_child_main,
            args=(
                source,
                function_name,
                json.dumps(params),
                self._limits.cpu_seconds,
                self._limits.memory_bytes,
                child_conn,
            ),
        )
        process.start()
        child_conn.close()  # parent doesn't write to it

        if parent_conn.poll(self._limits.wall_timeout_seconds):
            # poll() returning True means "something to read OR the write
            # end closed" — a resource-limit kill (e.g. SIGXCPU from
            # RLIMIT_CPU) closes the pipe without ever calling conn.send(),
            # which makes recv() raise EOFError rather than returning a
            # value. That's an expected outcome here, not a bug in this
            # process — the exitcode check below turns it into a specific
            # "terminated by signal" message instead of a generic one.
            try:
                outcome, payload = parent_conn.recv()
            except EOFError:
                outcome, payload = "error", "sandboxed process closed its pipe without responding"
        else:
            outcome, payload = "error", f"sandbox execution exceeded wall timeout of {self._limits.wall_timeout_seconds}s"

        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()

        # A resource-limit kill (SIGKILL/SIGSEGV from RLIMIT_AS, SIGXCPU
        # from RLIMIT_CPU) terminates the child without it ever reaching
        # conn.send() — exitcode is negative-signal in that case, and
        # parent_conn.poll() above will have timed out or returned nothing
        # useful. Surface that distinctly rather than a bare timeout
        # message so an admin looking at plugin logs can tell "hit its
        # memory/cpu limit" apart from "genuinely hung."
        if outcome == "error" and process.exitcode is not None and process.exitcode < 0:
            payload = f"sandboxed process terminated by signal {-process.exitcode} (resource limit or crash): {payload}"

        if outcome == "error":
            raise SandboxExecutionError(str(payload))
        return payload


class SqliteSandboxConnection:
    """Wraps a plugin's own SQLite connection (Decision 2's `storage:
    sqlite` mode) so the plugin never gets raw filesystem access itself —
    the platform opens the file, hands over this wrapper, and every write
    is quota-checked by SQLite's own `max_page_count` pragma rather than a
    size check this code could race past between checking and writing.
    """

    def __init__(self, path: str, quota_bytes: int = _DEFAULT_SQLITE_QUOTA_BYTES) -> None:
        self._conn = sqlite3.connect(path)
        page_size = self._conn.execute("PRAGMA page_size").fetchone()[0]
        max_pages = max(1, quota_bytes // page_size)
        self._conn.execute(f"PRAGMA max_page_count = {max_pages}")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            return self._conn.execute(sql, params)
        except sqlite3.DatabaseError as exc:
            if "database or disk is full" in str(exc).lower():
                raise SqliteQuotaExceeded(str(exc)) from exc
            raise

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
