# UmbrellaOS — Handoff to New Session (Phase 7 start)

Written at a deliberate handoff point (Phase 6 independently verified complete), not a crash/reset.
Same reasoning as the last handoff: fresh context window, token efficiency, one phase per chat.

## Where things actually stand

**Phase 0–6: complete on both services, independently verified — not just self-reported.**
- `umbrella-core`: **565/565** tests passing.
- `umbrella-discord`: **79/79** tests passing.

This isn't taken on faith from the building session's own summary. A separate reviewing pass (also me,
different context window) extracted both zips fresh, ran both suites itself, and specifically verified
the load-bearing claims against real source rather than trusting docstrings:
- Read `CallContext.from_discord_user()`'s actual implementation (not just its docstring) and confirmed
  the additive-permission-union design is real: `base_permissions | resolve_user_permissions(linked_user, db)`,
  correct `is_active` gate, correct `actor_type` distinction.
- Confirmed `identity.discord_delegate` (the permission gating Discord-delegated calls) is architecturally
  kept *outside* the Role/Permission table entirely — checked directly as an API-key scope in
  `registry/adapters/rest.py` — specifically so `owner`'s `ALL_PERMISSION_KEYS` inheritance can never
  quietly pick it up.
- **Adversarially broke a real call site** (deleted a `discord_user_id=...` line from `investigation_cog.py`)
  and confirmed `tests/test_discord_user_id_propagation.py` actually catches it — not just that the test
  exists and passes, that it's a genuinely working regression guard.
- Spot-checked `memory.maintenance.purge_expired`'s `destructive=True, reversible=False` flags, the
  `StaffEscalation.notified_at` column + migration `021`, the hosting confirmation view's fail-safe
  timeout behavior (`confirmed = False` on timeout, not left ambiguous), and the `discord.ext.tasks.loop`
  usage in the notification poller — all matched their claims exactly.

Nothing was found to walk back. Phase 6 is genuinely done.

## The one thing Phase 7 needs to know before assuming it's solved

**Phase 7's own roadmap text says:** *"Webhooks: subscribe to event-bus topics, signed payloads, retry
with backoff."* This assumes a real event bus exists. **It doesn't.** Phase 6's notification work
(`notifications_cog.py`) was deliberately, honestly scoped as a 60-second poller against
`moderation_intelligence.escalation.list` — not a push/event-bus system. Its own docstring says so
explicitly: *"core has no outbound path to Discord anywhere in this architecture."*

This is the same pattern that's shown up twice before in this project — the roadmap's prose describing
infrastructure that was never actually built (a Phase 2 event bus that Phase 5 discovered didn't exist;
a Phase 1 metrics time-series that also didn't exist and had to be built from scratch). Do not assume
Phase 6's polling satisfies Phase 7's "event-bus topics" requirement — verify this yourself before
building webhooks on top of an assumption. A real event bus (or an explicit, justified decision to build
webhooks against something else, like polling-based delivery) is a live open question for Phase 7 to
actually resolve, not inherited as already-decided.

## Also flagged, not fixed, separately from Phase 6:
`operational_intelligence`'s "escalated" flag never actually writes to `StaffEscalation` — confirmed
during Phase 6 by grep, only `moderation_intelligence` writes there. The notification poller can't
surface operational-intelligence escalations as a result. Untouched, real gap, still open.

## Phase 7's actual scope, per the roadmap (quoted in full, not paraphrased)

> - Public, versioned REST API (the same one the dashboard and bot use internally — no shadow API)
> - Webhooks: subscribe to event-bus topics, signed payloads, retry with backoff
> - Plugin/extension SDK: a documented extension point contract (hosting hooks, dashboard UI slots,
>   AI tool registration mirroring Moo's investigation-tool pattern) — sandboxed execution (resource
>   limits, no default filesystem/network access) so a third-party plugin can't become a security incident
> - Extension marketplace: listing/versioning/install flow, built on the SDK, not a special case
>
> **Definition of done:** a third party can write a plugin using only the published SDK contract,
> install it through the marketplace flow, and it runs sandboxed with no more access than it was granted.

**"AI tool registration mirroring Moo's investigation-tool pattern"** — the investigation domain
(`services/investigation/tools.py`, `capabilities/investigation.py`) built during Phase 5 is the literal
reference implementation this line points at: each tool is its own registered capability, aggregated by
`investigation.run`. Read that code before designing the plugin SDK's tool-registration contract — it's
not a metaphor, it's the pattern to generalize.

**"No shadow API"** — the Capability Registry (`registry/registry.py`, `registry/adapters/rest.py`) is
already the single source every REST route, CLI command, and now Discord command all flow through
(`registry/adapters/ai.py` for AI tool-calling, `bot/services/umbrella_core_client.py` for Discord). A
"public API" for Phase 7 should almost certainly mean *making this existing registry externally
reachable with proper scoping*, not building a second one. Verify this assumption before building
around it, same as everything else in this handoff — but it's the obvious continuity from every phase
so far.

## Real, substantive open questions carried forward from earlier Phase 5 discussion

Captured in `docs/adr/phase-7-notes-from-phase-5.md` (inside the `umbrella-core` zip), written when this
project first scoped Phase 7 conceptually, before any of it was built. Still accurate, still unresolved:

1. **Plugin package format**: zip (manifest + files), decided — not a container image. Means sandboxing
   must be runtime-enforced (resource limits, restricted builtins, no default filesystem/network), not
   physically isolated by the OS. Revisit if this proves insufficient in practice.
2. **Multi-surface plugins**: one plugin manifest should be able to declare a capability, a Discord
   command, and a dashboard UI slot together — not three separate artifacts. Confirmed intended shape,
   not yet built.
3. **Open gap, no decision made**: plugins bringing their own persistent data/schema. Three options were
   surfaced (generic key-value store; plugin-owned scoped migrations; a fully separate SQLite file per
   plugin) with real tradeoffs on isolation vs. query power — read the full reasoning in that file before
   picking one blind.
4. **Safety flag, must not be forgotten**: Moo's `CodeExecutionService` (ported into Phase 5, if it was —
   verify this was actually completed, the note doesn't confirm it was) claims subprocess isolation in
   its docstring but is actually a raw in-process `exec()` with full `__builtins__`, gated only by an
   owner-only permission check. **This must not become the template for Phase 7's plugin sandboxing.**
   Real process/container isolation, a restricted builtins allowlist, and enforced filesystem/network
   limits are needed for anything third-party-facing — none of which this pattern has.

## What's in this handoff, concretely

- `umbrella-core-PHASE6-COMPLETE.zip` — the verified, 565/565-passing core service.
- `umbrella-discord-PHASE6-COMPLETE.zip` — the verified, 79/79-passing Discord service.
- `moo-assistant-source.zip` — still worth having for reference (the investigation-tool pattern Phase 7's
  SDK should mirror lives there in its original form too), `.git` history and live `.env` credentials
  deliberately excluded as before.
- `original-daemon-and-dashboard/` — daemon and dashboard source, still untouched by any session so far.
  Phase 7's "hosting hooks" extension point will likely need to know the daemon's actual capability
  surface — this is where to look.
- `1785165890579_conversations.json` — the original architecture-design conversation. Largely historical
  now; the code is the more authoritative source of truth at this point.
- `umbrella-core-bug-report.md` — historical paper trail for 7 bugs found and fixed in an earlier round.
- `wheels/` — everything needed to install both services offline (confirmed `manylinux`, not `win_amd64`,
  every time this has been checked across this project's history).
- `roadmap-and-design-docs/` — read `UMBRELLAOS_MASTER_ROADMAP.md`'s Phase 7 section yourself (quoted
  above, but verify the quote against the source) before assuming scope from this doc alone.

## Working conventions that have consistently caught real bugs across this entire project

- **Test after every change, stop at the first new failure, never batch fixes hoping they all work.**
- **Verify claims by reading/running the actual code — including this document's own claims, and
  including a previous session's self-reported summary of its own work.** This exact discipline caught,
  across this project's history: a `TYPE_CHECKING`-guard that looked like a fix but didn't survive its
  own repro case; a naive/aware datetime bug hit three separate times, same fix each time; a broken
  concurrency-race fix with a second bug in its own error-recovery path; a flawed concurrency test that
  couldn't reliably simulate what it claimed to.
- **Flag real architectural decisions before building past them.** Multiple times, the roadmap's prose
  assumed infrastructure existed that didn't (Phase 2's event bus, Phase 1's metrics time-series, and now
  the Phase 7 webhooks-need-an-event-bus assumption above) — each got a stop-and-discuss, not a silent
  guess, with the reasoning preserved in code comments and `docs/adr/`.
- **Adapt reference code, don't port it uncritically.** Several real bugs were found and fixed by reading
  Moo-assistant's actual source critically rather than trusting its docstrings or reimplementing from
  memory — same standard applies to whatever Phase 7 reuses from the investigation-tool pattern.
