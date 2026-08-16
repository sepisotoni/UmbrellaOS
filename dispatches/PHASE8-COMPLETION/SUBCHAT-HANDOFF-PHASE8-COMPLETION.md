# UmbrellaOS — Sub-chat dispatch: Phase 8 completion (debugger + profiler + sandbox visualizer)

Read this, then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`, then
`MASTER-PROJECT-STATUS-AND-HANDOFF.md`. **Session label:
`subchat-phase8-completion`.**

Phase 8's SDK/sandbox/marketplace core is already done. Three things are
missing: a plugin debugger, a profiler, and a sandbox visualizer. Unlike
every dispatch since the bugfix one, **this one legitimately needs new
backend work** — checked directly in `services/plugins/sandbox.py`
before writing this doc: `ProcessSandbox.run()` returns only
`dict[str, Any]` (the plugin's actual result), with zero timing or
resource-usage telemetry captured anywhere. A profiler literally cannot
exist without this. Head chat and Sepiso Toni explicitly agreed backend
changes are in scope here — this is not scope creep, it's the task.

## Task A — Backend: execution telemetry (do this first, everything else depends on it)

In `services/plugins/sandbox.py`:
1. `ProcessSandbox.run()` needs to capture, per execution: wall-clock
   duration, CPU time consumed (you have `resource.RLIMIT_CPU` already
   set — look at whether `resource.getrusage()` in the child process
   before it exits gives you real consumed values, not just the limit),
   peak memory (same — `resource.getrusage().ru_maxrss`), and the
   outcome (`success` / `error` / `timeout` / a resource-limit kill —
   `_child_main`'s existing outcome strings are your starting point, read
   the whole function).
2. **Where does this data go?** Don't just return it inline in `run()`'s
   result dict (that would leak sandbox internals into a plugin's actual
   response payload, which is a real security-relevant boundary — a
   plugin should never be able to see or spoof its own resource-usage
   report). Instead: emit it separately — a new
   `PluginExecutionRecord` (or similar) written to a new table via a
   service call `run()` makes after execution completes, independent of
   what it returns to the caller. Check `models/` for the existing
   pattern other execution-adjacent records use (e.g. how
   `AuditEntryResult`'s underlying model is structured) before inventing
   a new one.
3. **New capability**, `plugin.sandbox.execution_history` or similar —
   paginated, filterable by `plugin_id`, returns the new records. Follow
   `platform.audit.search`'s exact params/pagination shape
   (`capabilities/system.py`) rather than inventing a different
   convention.
4. A migration for the new table — follow the existing alembic
   conventions (`umbrella-core-CURRENT/alembic/versions/`), and note:
   `dispatches/PHASE10-COMPLETION/`'s handback found 3 real bugs in this
   exact migration chain — read what it actually found before writing a
   new one, don't repeat them.
5. **Real tests.** This is new backend surface — needs the same coverage
   bar as anything else in this codebase, not lighter because it's
   "just telemetry." Test the actual `getrusage()` values are
   plausible (a plugin that sleeps 0.5s should show >0 CPU/wall time),
   test a plugin cannot see or tamper with its own record, test the
   capability's pagination/filtering.

## Task B — Plugin debugger

A way to inspect a specific execution after the fact — inputs given,
what happened, why it failed if it did. Given Task A's new execution
records, this is mostly a read/display problem once the data exists:
1. A capability to fetch one execution record's full detail (not just
   the list view Task A's `.execution_history` gives you) — including
   the actual error message/traceback if the outcome was `error` (check
   what `SandboxExecutionError` and its subclasses currently carry, and
   whether that detail is already captured anywhere or needs adding to
   Task A's record).
2. Dashboard UI: a detail view for one execution. Follow this app's
   established conventions — server component, permission-gated (pick
   the right permission, likely something under `plugin.sandbox.*` or
   reuse an existing marketplace one if it genuinely fits; state your
   reasoning either way), first-party trusted rendering (same "plain
   data, no raw HTML" rule every other first-party widget this session
   has followed — `activity-timeline.tsx` and `fleet-overview.tsx` are
   your two most recent examples).

## Task C — Profiler

Aggregate view over Task A's execution records — per-plugin stats
(average/p95 duration, memory, error rate over time), not just a single
execution's detail.
1. A capability for aggregated stats, grouped by `plugin_id` (and
   probably a time window — last 24h/7d, your call, state it).
2. Dashboard UI: a chart or table per plugin. Check what charting is
   already available in this app (`lib/nav-config.ts`'s dependencies, or
   just check `package.json` — if nothing's there, a plain table is
   fine, don't add a new charting library dependency just for this
   without flagging it first).

## Task D — Sandbox visualizer

A live-ish view of what the sandbox is actually doing — resource limits
configured (`ResourceLimits`'s real values — CPU seconds, memory bytes,
wall timeout — already exist as constants, this part's just surfacing
them, no new capture needed) alongside currently-installed plugins and
their *aggregate* profile from Task C. This is explicitly a dashboard
combining Task A/C's data with the marketplace's existing
`marketplace.install.list`, not a new data source of its own — if you
find yourself wanting new backend surface for this specific task beyond
what A/B/C already produce, stop and flag it, the aggregation should be
enough.

## What NOT to do

- Don't let a plugin's own sandboxed code access or tamper with its
  execution records (Task A point 2 — this is a real security boundary,
  not a style preference).
- Don't add a new charting library without flagging it first (Task C).
- Don't scope-creep into a live/streaming view for Task D — "aggregate,
  refreshed on page load" is the bar, not a websocket.

## Verification

Standard loop, both sides. This dispatch touches the backend for real —
after Task A, confirm the full suite is still green (should grow past
844, not just stay at it, given real new tests), `pip check` clean.
Frontend: fresh install, tsc/lint/build clean. Leak-check before every
commit.

## What to hand back

Same structure as every dispatch this session: handback doc + a `git
format-patch` diff, applies with `git am`, commit authored as
`subchat-phase8-completion`.
