# UmbrellaOS — Phase 7 Complete. Phase 8 Handoff.

**Superseded — see `PHASE9-COMPLETE-FOLLOWUP-HANDOFF.md`.** Phase 9 is now
done too; use `umbrella-core-PHASE9-COMPLETE.zip` as your code source, not
`umbrella-core-PHASE7-COMPLETE.zip` referenced below, which no longer
exists in this package. Kept for its Phase 7 build-history detail.

Phase 7 (v3 roadmap numbering — see
`roadmap-and-design-docs/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`, the
authoritative roadmap; ignore the older `UMBRELLAOS_MASTER_ROADMAP.md`, it's
marked superseded) is done: event bus, plugin SDK, sandboxing, REST API
exposure, webhooks, and marketplace, all built and independently re-verified —
not just self-reported — across five sessions. Use
`umbrella-core-PHASE7-COMPLETE.zip` as your code source. If you want the full
build history and the reasoning behind each design decision, read in order:
`handoff-to-new-session-phase7.md` → `-START.md` → `-PART2.md` → `-PART3.md` →
`-PART4.md`. If you just need current state to start Phase 8, this file plus
the code should be enough on its own.

**Final independent verification, this handoff:** applied the building
session's diff (`patch -p1`, zero fuzz/rejects across 19 files) to a fresh
extraction of the stated baseline, fresh venv, **exact pinned
`requirements.txt` dependencies** (the two prior sessions in this phase only
had unpinned-equivalent access due to no network in their sandboxes — this is
the first fully pin-accurate re-run of the whole Phase 7 test suite) —
**725/725 passing.** Also hand-tested the new zip-slip guard in
`services/plugins/source_store.py` with two crafted malicious zips (a `../../`
traversal entry and an absolute-path entry) — both correctly rejected before
manifest parsing.

## What Phase 7 built, end to end

- **Event bus**: durable outbox table (`events`), dispatcher with
  exponential backoff, closed the `operational_intelligence` escalation gap
  as its proof case.
- **Plugin SDK**: manifest schema (capabilities, Discord commands, dashboard
  UI slots, `storage: kv|sqlite`), tool-registration contract mirroring the
  Phase 5 investigation-tool pattern.
- **Sandboxing**: real OS-process isolation (`multiprocessing`/fork),
  enforced resource limits (CPU/memory/fd/fsize/nproc, wall-clock timeout),
  restricted builtins, SQLite disk quota via `PRAGMA max_page_count`.
  Adversarially probed by hand twice (a raw dunder-chain attempt, and the
  classic format-string two-stage gadget) — both failed to escape.
- **REST API exposure**: per-API-key rate limiting (additive on the existing
  per-IP check), confirmed the existing `ApiKey`/`/api/v1/` conventions were
  already sufficient — most of this item turned out to be config, not new
  endpoints, because of how Phase 0's registry auto-exposes every capability.
- **Webhooks**: `EventBus.subscribe_global()` — the real architectural
  addition, letting runtime-created `WebhookSubscription` rows reach the bus
  without static per-topic pre-registration. HMAC-SHA256 signed payloads,
  at-least-once delivery (documented trade-off), reuses the dispatcher's
  existing retry/backoff.
- **Marketplace**: `PluginListing`/`PluginVersion` (append-only)/
  `PluginInstall` models, local-disk zip storage with SHA-256 verification,
  `reload_installed_plugins()` on startup (tolerant of one corrupt install),
  full publish/install/update/uninstall lifecycle, and — per the decision you
  made explicitly rather than letting it default — `discord_commands`/
  `dashboard_ui_slots` are now genuinely queryable per-install via two
  discovery capabilities, not just validated-and-inert.

## The one real loose end Phase 7 leaves behind

**`umbrella-core` can now tell you what Discord commands or dashboard slots
an installed plugin declares — but nothing in `umbrella-discord` or the
dashboard repo consumes that yet.** This was flagged consistently across the
last two sessions as outside this code source's reach, not forgotten. Your
Discord-status-channel plugin idea specifically needs this closed before it's
real: the plugin's manifest and discovery data being correct doesn't yet mean
Discord actually shows a registered slash command, or the dashboard actually
renders a widget.

This is genuinely separate work, in a different repo, that hasn't been part
of any Phase 7 session — worth deciding whether it's a small side-quest before
Phase 8 starts, or explicitly deferred and tracked. Either is fine; picking
one deliberately (like every other real decision this phase) is what matters.

## Phase 8 — Observability & Security Hardening (v3 numbering)

Full spec is in the consolidated roadmap doc under Phase 9 — wait, check
this carefully: **the roadmap's Phase 9 is Observability/security hardening,
not Phase 8.** What these handoff docs have been calling "Phase 7" this whole
build actually covered the roadmap's Phase 7 *and* 8 combined (public
API/webhooks was v3 Phase 7; plugin SDK/sandboxing/marketplace was v3 Phase
8) — see the consolidated roadmap's own explicit note about this numbering
gap. So: **what comes next, in roadmap terms, is v3 Phase 9.** Read its full
section in `UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md` before scoping
anything — Prometheus/OTel/Grafana, log aggregation + search, threat
detection, hardened plugin sandboxing based on real Phase 8 usage,
dependency/CVE scanning, WAF-style API hardening.

Two things worth deciding before that session starts building, the same way
Phase 7's event-bus/plugin-storage/marketplace questions got decided up
front rather than defaulted:

1. **Metrics/tracing backend choice** — self-hosted Prometheus+Grafana
   (matches the single-node, no-daemon-on-ACLClouds reality) vs. a hosted
   option. Given the project's consistent preference for owning
   infrastructure it can run without external dependencies (SQLite over a
   managed DB, local disk over S3 for plugins), self-hosted is the likely
   answer, but it's worth stating deliberately rather than assuming.
2. **What "threat detection" concretely means for a single-operator
   Minecraft-server-admin platform** — the roadmap line is generic
   (anomalous auth patterns, brute-force alerting). Scoping this too broadly
   risks building enterprise SIEM-shaped tooling nobody will tune; scoping it
   to "alert on the failure patterns that actually matter for this project's
   threat model" (the same "assume internet-exposed, assume malicious users"
   framing from Phase 0 onward) is probably the right size — but that's a
   real scoping decision, not obvious from the roadmap line alone.

## Working conventions (unchanged across every phase so far, still binding)

Test after every change, stop at the first new failure, don't batch. Verify
claims against real code — every session in this project, including this
one's own summary, gets independently re-checked, not trusted by default.
Flag real design decisions before building past them. Hand back changes as a
diff/manifest package with `patch -p1` instructions, not a full re-export —
it's been consistently faster and safer to verify this way since Part 3.
Strip `.env`/`umbrella.db` before zipping, even empty/placeholder ones.
