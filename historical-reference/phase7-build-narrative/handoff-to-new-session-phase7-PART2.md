# UmbrellaOS — Phase 7 Handoff, Part 2: Plugin SDK + Sandboxing + Marketplace

Read in this order: `handoff-to-new-session-phase7.md` (Phase 0–6 verification),
`handoff-to-new-session-phase7-START.md` (Decision 1 event bus, Decision 2 plugin
storage — both now **built**, not just decided), then this file for exactly where
the previous session left off and what's left.

**Superseded — see `handoff-to-new-session-phase7-PART3.md`.** The plugin SDK and
sandboxing work this file describes as "not yet built" is now done; use
`umbrella-core-PHASE7-SDK-SANDBOX-COMPLETE.zip` (in this package) as the current
code source, not the zip name below, which no longer exists in this package. This
file is kept for its still-accurate event-bus/escalation-fix history and the
Decision 1/2 detail PART3 doesn't repeat. This was independently re-verified by a
separate reviewing pass — merged the session's file-level diff onto the Phase 6 tree,
built a fresh venv from scratch, and re-ran the full suite personally rather than
trusting the session's self-report: 582/582 passing, confirmed. Also spot-checked
with pyflakes; nothing new is broken beyond already-known pre-existing hygiene debt
(see the cleanup section below) and two intentional side-effect imports
(`services/events/__init__.py` importing `.subscribers`, and `main.py` importing
`services.events`) that exist specifically to trigger subscriber registration at
startup — flagged by pyflakes as "unused" but correct as written.

## What's done (verified, not self-reported)

**Environment / dependency fixes, both real and now fixed in the repo itself:**
- `cryptography` was completely missing from `umbrella-core/requirements.txt` despite
  `services/secrets_service.py` needing it — added, pinned to the version actually
  verified to install cleanly (not guessed).
- `aioredis==2.0.1` removed — confirmed genuinely dead code. The app uses
  `redis.asyncio` (part of the standard `redis` package), and `fakeredis`'s own
  `fakeredis.aioredis` submodule only needs `redis` + `sortedcontainers`, not the
  standalone `aioredis` package. This was a real unused dependency, not a
  might-be-needed-later one.
- `asyncpg`, `psycopg2-binary`, `pyjwt` — investigated and left alone. Their pins are
  correct; the earlier install failures were the bundled offline `wheels/` folder
  being stale/incomplete, not a `requirements.txt` problem. Don't re-fix what wasn't
  broken.
- Confirmed clean in a from-scratch fresh venv — no manual intervention needed to get
  to 582/582.

**Decision 1 (event bus) — fully built and tested:**
- `models/events.py` — `Event` outbox model (`id`, `topic`, `payload_json`,
  `created_at`, `dispatched_at`, `attempts`, plus `next_attempt_at` added beyond the
  originally locked schema for exponential backoff — deliberate addition, documented
  in the dispatcher's docstring, not a silent scope-creep).
- `alembic/versions/022_events_outbox.py` — migration for the above.
- `services/events/bus.py` — `EventBus.publish()` (writes in the caller's existing
  transaction, no separate commit — this is what makes it a true outbox, not just a
  queue) and `EventBus.subscribe()`/`subscribers_for()` (process-wide in-memory
  registry).
- `services/events/dispatcher.py` — `EventDispatcher.dispatch_pending()` (batch fan-out
  with exponential backoff) and `run_event_dispatcher_loop()` (same stop-event shape as
  the existing `services/scheduler_loop.py`, deliberately mirrored).
- `services/events/subscribers.py` — one real subscriber so far: a structured log line
  on `staff_escalation.created`, proving the fan-out path actually executes a handler
  end to end. This is the seam webhooks and plugin event handlers plug into next.
- Wired into `main.py`'s lifespan alongside the existing scheduler/sampler loops.
- 13 new tests (`test_event_bus.py`, `test_event_dispatcher.py`), all passing.

**Proof case — `operational_intelligence` escalation gap — closed and tested:**
- `services/operational_intelligence/postmortem.py` and `nl_query.py` both now write a
  `StaffEscalation` row and publish a `staff_escalation.created` event, in the same
  transaction, when `Orchestrator.run()` escalates. Previously this signal was computed
  and silently discarded — confirmed via grep during Phase 6 review, now actually fixed.
  4 new tests cover both escalated and not-escalated paths for both call sites.
- `StaffEscalation`'s model docstring updated to list "operational" as a real source
  (was stale, listed only the original three).

**Deliberately left alone, confirmed correct to leave:**
- `notifications_cog.py` still polls `moderation_intelligence.escalation.list` directly
  rather than subscribing through the new event bus/topic model. This is intentional —
  it already receives the newly-fixed operational escalations for free (same
  `StaffEscalation` table), so there's no functional gap left to justify a migration
  mid-phase. Migrating Discord onto the topic abstraction is real, separate work with
  its own regression surface — treat it as later-phase scope, not something this
  handoff silently expects the next session to do. If you disagree with this read,
  that's fine, but make it a deliberate decision, not an assumption.

## What's left in Phase 7

1. **REST API exposure for the event bus** — webhook registration (CRUD for
   subscriber URLs per topic) and a real delivery worker subscriber (HTTP POST with
   retry/backoff, reusing the dispatcher's existing `attempts`/backoff shape). Only the
   logging subscriber exists today; webhooks are still just a plan.
2. **Public, versioned REST API exposure** more broadly — making the existing
   Capability Registry externally reachable with proper scoping. Not yet started. Read
   `registry/registry.py` and `registry/adapters/rest.py` first — this should almost
   certainly mean exposing the existing registry, not building a second API surface.
3. **Plugin SDK — tool-registration contract.** Not yet designed or built. The
   reference pattern to mirror is `services/investigation/tools.py` +
   `capabilities/investigation.py` (each diagnostic is a small class registered as its
   own capability via `_make_tool_capability`'s boilerplate generator, aggregated by
   `investigation.run`, and individually exposed via the AI tool registry's
   `list_tools()`). Read both files before designing anything — don't design from this
   summary alone.
4. **Plugin sandboxing — the actual execution boundary.** Decision 2 (manifest-declared
   `kv`/`sqlite` storage) is locked and documented in the START doc, but nothing about
   *running* third-party plugin code safely has been built yet. This is the
   security-critical piece of Phase 7. Hard constraint, not a suggestion: must not
   follow the pattern of Moo-assistant's `CodeExecutionService`, which claims subprocess
   isolation in its docstring but is actually a raw in-process `exec()` with full
   `__builtins__`, gated only by an owner-only permission check. Real isolation
   (restricted builtins allowlist at minimum; process or container isolation preferred
   if feasible within the zip-package plugin format already decided on), enforced
   resource limits (including the per-plugin SQLite disk quota decided in Part 1), and
   no default filesystem/network access are all required, not aspirational.
5. **Marketplace** (listing/versioning/install) — not started at all. Sequentially
   depends on the SDK being solid, since install-time logic needs to read a plugin's
   manifest (including its `storage` field) and provision accordingly.

## Known non-blocking cleanup (optional, do not let this consume Phase 7 budget)

A code review across Phases 0–6 (pyflakes + targeted checks, not just reading test
counts) found no undefined names, no duplicate route registrations, and no duplicate
Alembic revision IDs anywhere in either service — nothing here is a landmine. What it
did find, purely cosmetic:
- ~40 unused imports scattered across core's routers/services/models.
- Two harmless import redefinitions worth a one-line fix each:
  `services/settings_service.py` imports `sqlalchemy.update` at module level but never
  uses it (the file's own `SettingsService.update()` static method is unrelated —
  just delete the dead import); `services/anticheat_service.py` has a dead top-level
  `import os` shadowed by a legitimate local re-import inside a function — remove the
  outer one.
- `_format_error`/`_format_result` helpers are re-implemented per-cog in the Discord
  bot (9 and 4 times respectively) rather than shared from a common base — a real DRY
  opportunity, not urgent.
- One live, well-documented TODO in `services/ai/orchestrator.py:147` — the AI
  orchestrator currently only generates/dual-reviews text and never invokes a
  capability itself, so `action_guard` has nothing to guard yet. It correctly points to
  `registry/adapters/ai.py`'s `call_tool()` as the integration point any future
  "AI executes a capability" feature must go through. Directly relevant to item 3
  above (plugin SDK's AI tool registration) — worth rereading when you get there,
  not something to fix now.

None of this blocks Phase 7. Fix opportunistically if touching a file anyway; don't
go looking for it as separate work while there's real scope left.

## Working conventions (unchanged, still binding)

Test after every change, stop at the first new failure, don't batch fixes. Verify
claims against real code — including this document's claims, and including any
previous session's self-reported summary of its own work, including this one's.
Flag real architectural decisions before building past them (the plugin
sandboxing execution model in item 4 above is the next one likely to need this).
