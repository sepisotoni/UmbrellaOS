# UmbrellaOS — Phase 7 Handoff (design decisions locked, ready to build)

This supersedes `handoff-to-new-session-phase7.md` for scope purposes — that file's
verification of Phase 0–6 (565/565 core tests, 79/79 discord tests, independently
re-verified against real source, not self-reported) still stands and should be read
first for context. This file exists because the open design questions that doc raised
have now been discussed and decided. Nothing below should be re-litigated from
scratch — if something here looks wrong once you're reading real code, flag it and
stop, don't silently override a decision that was made deliberately.

## Decision 1: Event bus — durable outbox table (not a broker, not pure polling-fanout)

**What to build:**
- An `events` table: `id`, `topic`, `payload_json`, `created_at`, `dispatched_at`
  (nullable), `attempts`, `last_error` (nullable).
- Any domain that needs to emit an event writes to this table **in the same DB
  transaction** as the state change it's recording — this is the entire point of the
  outbox pattern: an event can never be dropped between the state change committing
  and the event being recorded, because they're the same transaction.
- A single dispatcher task, structurally the same shape as Phase 6's proven
  `notifications_cog.py` 60-second poller — reads undispatched rows, publishes to
  in-process subscribers, marks `dispatched_at`, retries with backoff via `attempts`
  on failure.
- Subscribers to this bus: the existing Discord notifier (migrate it from polling
  `StaffEscalation` directly to subscribing to a topic), registered webhooks (Phase 7's
  actual deliverable), and future plugin event handlers (Phase 7 SDK).

**Why this and not the alternatives** (don't re-open this without new information):
a real broker (Redis Streams etc.) is infrastructure to run/monitor/fail-over that a
single-node deployment doesn't need until Phase 9 clustering gives a real reason.
Pure in-memory pub/sub loses events on restart between fire and receive, and doesn't
honestly satisfy the roadmap's actual "subscribe to event-bus topics" language — it'd
be polling-fanout wearing an event-bus costume, the same kind of prose/reality gap
that's already bitten this project twice (Phase 2's assumed event bus, Phase 1's
assumed metrics time-series).

**First real test case, not deferred separately:** `operational_intelligence`'s
"escalated" flag currently never writes to `StaffEscalation` — only
`moderation_intelligence` does (confirmed by grep during Phase 6, left open). Do not
patch this against the old poller-per-target pattern. Once the `events` table and
dispatcher exist, close this gap by making `operational_intelligence` emit an event on
escalation, same as `moderation_intelligence` should. This proves the bus works
end-to-end against a real, already-flagged gap instead of only synthetic events.

## Decision 2: Plugin persistent data — hybrid, manifest-declared

Not a single storage model for every plugin. The plugin manifest declares which mode
it wants:

- **`storage: "kv"` (default)** — namespaced JSON key-value store, one shared table
  (`plugin_id`, `key`, `value_json`). No schema of its own, no migrations. Covers most
  plugins (settings, counters, simple state).
- **`storage: "sqlite"`** — plugin gets its own SQLite file, created and owned by the
  *platform* at install time (path like `data/plugins/{plugin_id}/plugin.db`), handed
  to the plugin as a connection object through the SDK — the plugin never gets raw
  filesystem access itself. This is what keeps "no default filesystem access" true
  even though the plugin effectively has a real database.

Rules that must hold regardless of mode (part of the sandboxing contract, not
optional):
- SQLite file size counts against a per-plugin disk quota — otherwise it's an
  unbounded resource with no sandboxing story.
- No cross-plugin or cross-core joins in either mode, ever, by design. A plugin
  needing core data goes through the Capability Registry/API like everything else
  does — that boundary is what makes "sandboxed, no more access than granted" actually
  true rather than aspirational.
- The marketplace install flow must read the manifest's `storage` field and provision
  accordingly (create the KV namespace, or create+hand off the SQLite file) — this is
  real install-flow logic, not just metadata sitting unused in the manifest.

## Everything else from the prior handoff still applies, unchanged

Read `handoff-to-new-session-phase7.md` in full before starting. In particular, still
true and still binding:

- **"No shadow API"**: the Capability Registry (`registry/registry.py`,
  `registry/adapters/rest.py`) is the existing single source of truth every route/CLI
  command/Discord command already flows through. Phase 7's "public API" should almost
  certainly mean making this registry externally reachable with proper scoping — not
  building a second one. Verify this against the real code before building around it.
- **AI tool registration** should mirror the `investigation.run` pattern from
  `services/investigation/tools.py` / `capabilities/investigation.py` (Phase 5) —
  read that code before designing the plugin SDK's tool-registration contract.
- **Sandboxing must not follow Moo's `CodeExecutionService` pattern** — that code
  claims subprocess isolation in its docstring but is actually a raw in-process
  `exec()` with full `__builtins__`, gated only by an owner-only permission check.
  Real process/container isolation, a restricted builtins allowlist, and enforced
  filesystem/network limits are required for anything third-party-facing.
- Plugin package format is zip (manifest + files) — already decided, not a container
  image. Sandboxing is therefore runtime-enforced, not OS-level isolation.
- One plugin manifest can declare a capability, a Discord command, and a dashboard UI
  slot together — confirmed intended shape, not yet built.

## Working conventions (carried forward, still binding)

- Test after every change, stop at the first new failure, never batch fixes hoping
  they all work.
- Verify claims by reading/running the actual code — including this document's own
  claims, and including any previous session's self-reported summary of its own work.
- Flag real architectural decisions before building past them. The two decisions in
  this document are the result of that discipline being applied to Phase 7 already —
  don't skip it for whatever the *next* ambiguous thing turns out to be.
- Adapt reference code (Moo-assistant, the investigation-tool pattern), don't port it
  uncritically.

## What's in this handoff package, concretely

Same contents as the prior `UMBRELLAOS-PHASE7-HANDOFF.zip`:
- `umbrella-core-PHASE6-COMPLETE.zip` — verified, 565/565-passing core service.
- `umbrella-discord-PHASE6-COMPLETE.zip` — verified, 79/79-passing Discord service.
- `moo-assistant-source.zip` — reference for the investigation-tool pattern.
- `original-daemon-and-dashboard/` — daemon + dashboard source, still untouched;
  needed for Phase 7's "hosting hooks" extension point.
- `1785165890579_conversations.json` — original architecture-design conversation,
  historical context only; code is the authoritative source now.
- `umbrella-core-bug-report.md` — historical paper trail, already-fixed issues.
- `roadmap-and-design-docs/` — read `UMBRELLAOS_MASTER_ROADMAP.md`'s Phase 7 section
  and `docs/adr/phase-7-notes-from-phase-5.md` (inside the core zip) yourself before
  assuming scope from any summary, including this one.
- `wheels/` — offline install for both services (confirmed `manylinux`, not
  `win_amd64`).
- `handoff-to-new-session-phase7.md` — the prior handoff, still required reading for
  Phase 0–6 verification detail this file doesn't repeat.
- This file — the design decisions that make Phase 7 buildable without re-litigating
  the event bus / plugin storage questions from a blank slate.
