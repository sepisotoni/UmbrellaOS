"""
models/plugin_execution.py — PluginExecutionRecord: one row per sandboxed
plugin execution, capturing timing/resource-usage telemetry and outcome.

Phase 8 completion, Task A. Deliberately a separate table from anything
`ProcessSandbox.run()` returns to its caller — see that module's `run()`
docstring for the security reasoning (a plugin must never be able to see
or spoof its own resource-usage report, so this is written by
`services/plugins/sandbox.py` itself, after execution, independent of the
result payload that crosses back into `services/plugins/registration.py`'s
handler wrapper).

Modeled on `models/audit_log.py` (append-only, no update/delete) and
`models/security_event.py` (a raw per-event signal feed, not aggregated at
write time — Task C's profiler aggregates over these rows at query time
instead).

`outcome` vocabulary, matching `ProcessSandbox`'s own classification of a
`SandboxExecutionError`'s message text (see `sandbox.py::_classify_outcome`):
    "success"             — entrypoint ran and returned a valid result
    "error"                — an uncaught plugin exception, missing
                              entrypoint, or a non-dict return value
    "timeout"              — killed for exceeding the wall-clock timeout
    "resource_limit_kill"  — killed by RLIMIT_CPU/RLIMIT_AS (SIGXCPU/SIGKILL)

`cpu_time_ms` / `peak_memory_bytes` are nullable: for "timeout" and
"resource_limit_kill" outcomes, the child process is terminated by signal
before it ever reaches the code that would report its own
`resource.getrusage()` values back over the pipe — there is no process
left to ask. Honest limitation, not an oversight (see `sandbox.py`'s own
module docstring for the same "state it plainly" convention used
elsewhere in this domain). `wall_time_ms` is always populated — it is
measured in the parent process (`ProcessSandbox.run()`), independent of
whether the child ever responds.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from database.engine import Base


class PluginExecutionRecord(Base):
    __tablename__ = "plugin_execution_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    plugin_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entrypoint: Mapped[str] = mapped_column(String(256), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # success | error | timeout | resource_limit_kill
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    wall_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_memory_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # The uncaught exception's str(), or SandboxExecutionError's message
    # for a timeout/resource-limit kill. Null only for "success". This is
    # the field Task B's debugger detail view exists to surface — never
    # returned as part of a capability's normal (audited) result payload,
    # only through the dedicated read capability below.
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<PluginExecutionRecord plugin_id={self.plugin_id!r} outcome={self.outcome!r}>"
