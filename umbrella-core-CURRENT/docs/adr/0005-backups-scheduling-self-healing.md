# ADR-0005: Backups, scheduling, and self-healing as capability composition, not bespoke systems

**Status:** Accepted, implemented (Phase 4).

## Context

Phase 4 needed a sandboxed file manager, backups, scheduled automation, crash-recovery/self-healing,
and secrets encryption. The master roadmap explicitly split backup *execution* (daemon-side) from
backup *metadata/scheduling* (core-side), and separately called for "self-healing" without prescribing
its mechanism.

## Decisions

**Files and backups are daemon-enforced, not UI-enforced.** `internal/files.Manager` resolves every
relative path against a fixed root and rejects anything — `..` traversal, disguised traversal through
subdirectories, absolute paths, or a symlink pointing outside the sandbox — that would escape it.
`internal/backup`'s restore path applies the equivalent defense against tar-slip (a maliciously crafted
archive entry escaping the restore destination). Both were proven against real attack constructions in
tests, not just plausible-looking ones — including one genuine false-positive caught by the tests
themselves: an archive entry named like an absolute path (`/etc/cron.d/evil`) turned out to already be
safely contained by Go's `filepath.Join` semantics, discovered by writing a test that assumed otherwise
and watching it fail, then verifying the real behavior empirically before "fixing" a test that was
actually wrong, not the code.

**The scheduler is generic — it names a capability and fixed params, not "a backup schedule."** Any
capability already reachable through Phase 0's registry becomes schedulable for free, on a cron
expression, with zero schedule-specific plumbing per capability. `SchedulerService.run_schedule` fires
through the exact same `registry.call()` path a REST or CLI caller would use, with a system-level
`CallContext` (`CallContext.from_system`) — superuser, since a schedule's own creation already required
whatever permission its target capability needs; the scheduler isn't re-deriving authorization on every
tick, it's exercising authorization that was already granted when the schedule was created.

**Self-healing is a capability (`hosting.fleet.reconcile`), scheduled like anything else — not a
separate always-on watchdog process.** This is the concrete answer to the roadmap's "self-healing"
requirement: it composes the crash-classification logic with the existing scheduler infrastructure
rather than inventing a third execution model. An operator schedules it (`automation.schedule.create`
pointing at `hosting.fleet.reconcile`, e.g. every minute) the same way they'd schedule a nightly backup.

**Escalating backoff, not infinite auto-restart.** `crash_count` tracks *consecutive, unattended*
crashes — reset to zero on any operator-initiated start/restart, not a lifetime tally — and a server is
suspended (not restarted again) after `MAX_CONSECUTIVE_CRASHES_BEFORE_SUSPEND` (3) consecutive crashes.
An unbounded restart loop against a genuinely broken server would otherwise burn resources forever and
alert nobody, since each individual restart "succeeds" from the daemon's point of view even though the
server immediately crashes again.

**Secrets encryption covers `Node.signing_secret` specifically, not `Server.env_overrides` blanket.**
`env_overrides` mixes genuine secrets with ordinary config; encrypting the whole dict would make
non-secret values opaque for no benefit. A per-key "mark this env var as secret" design is real,
deliberately deferred follow-up, not an oversight.

## A real bug this phase caught and fixed, not glossed over

`Backup.created_at` originally used `server_default=func.now()`, which is second-resolution under
SQLite. Two backups created within the same second — exactly what the Phase 4 scheduler firing
multiple jobs in one tick could produce — were genuinely unorderable: no combination of
`created_at DESC` and the UUID primary key (uuid4 is random, carries no time information) could tell
them apart. Found via a failing test, not by inspection. Fixed by switching to a Python-side
`datetime.now(timezone.utc)` default, computed at object-construction time with microsecond resolution
— portable across SQLite and Postgres identically, rather than relying on either engine's specific
timestamp precision.

## Consequences

**What this buys:** the scheduler, backups, and self-healing all reuse the same registry call path,
audit logging, and permission model every other capability already has — there was no "automation
subsystem" to build with its own authorization/audit story, because Phase 0's registry already
generalizes to this.

## Alternatives considered

- **A dedicated cron-like process/container separate from `umbrella-core`**: rejected — it would need
  its own authentication story to call capabilities, duplicating what the registry already provides to
  every in-process caller for free.
- **Encrypting `Server.env_overrides` wholesale**: rejected for the reason stated above; noted as
  explicit follow-up, not silently out of scope.
- **A raw autoincrement integer tiebreaker column for `Backup` ordering**: considered when the timestamp
  bug was found, rejected — SQLite has no portable equivalent to a Postgres `Sequence` bound to a
  non-primary-key column, and the Python-side microsecond timestamp fix is simpler and equally correct
  without introducing an engine-specific mechanism.
