# UmbrellaOS Master Roadmap — v3, consolidated (this is the doc to read)

This file supersedes both `UMBRELLAOS_MASTER_ROADMAP.md` (v2 — 10 phases, kept only
for its still-useful phase-7/8/9 write-ups, referenced by number below) and the
roadmap table embedded in `UMBRELLAOS_ECOSYSTEM_ARCHITECTURE.md` (v3's original
home, one-line-per-phase only). **Numbering below is v3's — 13 phases, 0–12 — since
v3 is the deliberately-corrected version** (moved the Capability Registry to Phase 0,
split the old combined Phase 7 into two, added a phase that didn't exist before).
If you only remember one thing from this file: **v2's phase numbers do not match
these.** v2's Phase 7 = this doc's Phase 7 *and* 8 combined. v2's Phase 8 = this
doc's Phase 9. v2's Phase 9 = this doc's Phase 11. v2's Phase 10 = this doc's
Phase 12. Don't cite a v2 phase number in new work — cite this doc's.

Definition-of-done standard (applies to every phase below, stated once rather than
repeated per phase, per the original v3 doc's own convention): a phase is done when
every capability it introduces is declared through the registry (already
CLI+API+AI-reachable, not "will add CLI later"), every destructive/irreversible
capability is correctly flagged, every capability has an actually-enforced
permission requirement (not a placeholder), audit events are visible for everything
the phase touches, and no code path works through only one adapter because business
logic leaked into it instead of staying in the service layer.

---

## Phase 0 — Platform Contract ✅ done
Capability Registry, adapter codegen (REST/CLI/AI-tool from one declaration), base
RBAC/audit primitives, `CallContext` model. Everything else depends on this.

## Phase 1 — Daemon Core & Environment Abstraction ✅ done
## Phase 2 — Hosting Control Plane ✅ done
Nodes/servers/allocations/templates, node groups/labels/regions as foundational
metadata (pulled forward from the clustering phase deliberately, so Phase 11 doesn't
have to retrofit them), event bus, audit domain.

## Phase 3 — Identity, Access & Dashboard Hosting UI ✅ done
OAuth/OIDC/MFA/API keys, RBAC, dashboard hosting UI.

## Phase 4 — Files, Backups, Disaster Recovery & Automation ✅ done
Scheduler/automation, self-healing, secrets.

## Phase 5 — AI Operating System Layer ✅ done
Ported Moo domains, Tool Registry integration, continuous diagnostics/forecasting/
security-audit services, full AI copilot capability set.

## Phase 6 — Discord & Unified Notification Fabric ✅ done

## Phase 7 — Developer Platform I: Public API & Integrations 🔶 in progress
**Component:** `umbrella-core` domain `platform` (this is the first half of what
v2 called "Phase 7" — the public-facing/integration half)

- Public, versioned REST API — the same one the dashboard and bot use internally,
  exposed externally with proper scoping (no shadow API)
- Generated official SDKs, full CLI surface
- Webhooks: subscribe to event-bus topics, signed payloads, retry with backoff
- Terraform provider — sequenced here deliberately, *after* the public API is
  stable, since it's a thin generated client over that API's schema; building it
  before the API stabilizes means rebuilding it

**Definition of done (specific to this phase, in addition to the standard above):**
a third party can authenticate against the public API with a scoped, revocable
credential, call any exposed capability, and subscribe to a webhook topic that
reliably delivers signed, retryable payloads.

## Phase 8 — Developer Platform II: Plugin SDK & Marketplace 🔶 in progress
**Component:** `umbrella-core` domain `platform` (the second half of v2's old
combined "Phase 7" — the third-party-code-execution half)

- Plugin/extension SDK: documented extension point contract (hosting hooks,
  dashboard UI slots, AI tool registration mirroring Moo's investigation-tool
  pattern)
- Sandboxed execution: resource limits, no default filesystem/network access, so a
  third-party plugin can't become a security incident
- Extension marketplace: listing/versioning/install flow, built on the SDK, not a
  special case
- Plugin debugger/profiler, sandbox visualizer

**Definition of done:** a third party can write a plugin using only the published
SDK contract, install it through the marketplace flow, and it runs sandboxed with
no more access than it was granted.

## Phase 9 — Observability & Security Hardening
**Component:** cross-cutting, `umbrella-core` + `umbrella-daemon`
*(full detail carried forward from v2's Phase 8 — scope is unchanged, only the
number moved)*

- Metrics: Prometheus-format exposition from core and daemon; Grafana-compatible
  dashboards shipped as a starting point, not left as an exercise
- OpenTelemetry tracing across core ↔ daemon ↔ dashboard request paths
- Log aggregation + full-text search across core/daemon/server logs — one
  searchable index, not a per-subsystem grep
- Threat detection: anomalous auth patterns, brute-force/rate-limit-violation
  alerting, tied into the Phase 6 notification fabric
- Plugin sandboxing hardened further based on real Phase 8 usage; dependency/CVE
  scanning in CI
- WAF-style hardening at the API gateway (request validation, size limits,
  known-bad-pattern blocking) — pragmatic hardening, not a claim of enterprise WAF
  parity

**Definition of done:** an operator can trace a single request across every service
that touched it, search logs platform-wide, and see a Grafana dashboard populated
from real metrics with zero manual wiring.

## Phase 10 — Unified Experience Layer (full dashboard rewrite — scope locked)

**Component:** `umbrella-dashboard`, replacing the current implementation
entirely, not extending it.

**This phase's scope changed from "unspecced" to locked as of this note.**
Two things converged: (1) the existing dashboard was found to descend directly
from the pre-rebuild `UmbrellaMC` codebase (uploaded as reference material at
this project's very start, then used as a literal starting point when Phase 3
built the dashboard, rather than as inspiration only) — it's carried real bugs
and datedness forward ever since, untouched by any session since Phase 3 while
the backend evolved underneath it across five more phases; and (2) Phase 10's
own feature list (command palette, search, topology map, custom dashboards)
was never going to retrofit cleanly onto that foundation anyway. Rather than
rewrite twice — once to fix the old dashboard, again to add Phase 10's
features on top — this phase is now explicitly: **one full rewrite that is
also where Phase 10's new concepts get built in from the start**, not bolted
on after.

**Confirmed, not using v0 or any external mockup tool** — build directly
against this project's real backend (capability registry, RBAC role ladder,
actual API shapes), not a generic scaffold disconnected from it.

**Explicitly not carrying forward without re-evaluation:** the current
`'use client'`-on-nearly-every-page pattern (flagged as the likely cause of
the existing dashboard's slow-load complaints — Next.js 16's server-rendering
default was being opted out of almost everywhere). The rewrite should default
to server components and scope `'use client'` to genuinely interactive leaf
components, per the reasoning already written into
`DASHBOARD-PLUGIN-UI-SCOPING.md`.

**Original scope, still the spec for what this phase covers:**
- Command palette, global search, activity timeline, live topology map,
  dependency graph, fleet overview, custom dashboards/widgets, workspace
  layouts
- Plus, folded in from the marketplace plugin-UI scoping work: the three-tier
  plugin UI model (widgets → config toggles → owned pages) from
  `DASHBOARD-PLUGIN-UI-SCOPING.md` — that doc's decisions (schema-driven
  rendering only, no plugin-supplied markup, `app/marketplace` naming,
  generic dynamic-route strategy for owned pages) still apply; only the
  target codebase changed from "extend the existing app" to "build fresh."

**Prior work that carries forward despite the code being discarded:** a
session was mid-flight building Tier-1 marketplace widgets directly against
the old dashboard when this rewrite decision was made. Its actual page code
is not being used. What it may have learned about the real response shape of
`marketplace.install.list`/`marketplace.install.dashboard_slots` (whether it
matched what the scoping doc assumed) is worth carrying into the rewrite if
captured before that session was stopped — check for that before assuming the
scoping doc's API assumptions are unverified.

**Open questions — now answered and locked, not open anymore:**

1. **Live topology map: both infrastructure and capability dependencies,
   combined in one experience — as two toggleable layers over the same
   canvas, not one mixed graph** (locked). Infrastructure layer (Phase
   2's node/server topology) and dependency layer (Phase 8's
   plugin/capability graph) are switchable views over the same canvas
   rather than one graph with mixed node/edge semantics — keeps each
   layer's visual language clean (infra nodes and capability-dependency
   edges don't have to share one confusing legend).

2. **Custom dashboards/widgets: both** — the plugin-widget system (Tier
   1-3, already scoped in `DASHBOARD-PLUGIN-UI-SCOPING.md`) supplies the
   *content*, but users can also arrange their own personal layout on top
   of it, **per-page (not one global home dashboard), pre-populated with
   a sensible default rather than a blank canvas** (locked). Real
   implications this creates, still needing definition before building:
   - Persistence model is `(user_id, page_id, layout_json)`, not just
     `(user_id, layout_json)` — meaningfully more storage/state than a
     single global layout would have needed.
   - **Which pages are actually customizable is still undefined** —
     per-page customization doesn't mean literally every page (a login
     screen or a single-record detail page has no obvious use for it).
     Whoever builds this needs to explicitly enumerate which pages get
     the customization affordance, not assume "all of them."
   - "Sensible pre-populated default" is real content-design work per
     customizable page, not a technical flag — someone has to decide what
     the default widget selection/arrangement actually is for each page,
     ideally informed by what that page's most-used data actually is.
   - Still needed regardless of the above: a per-user layout persistence
     model, a drag-and-drop arrangement UI, and a widget picker/catalog
     experience distinct from the marketplace install flow (installing a
     plugin ≠ choosing to place its widget on a given page's layout).

3. **Global search: both, federated into one search UI — via live
   fan-out per keystroke, not a pre-built index** (locked). Simpler to
   build (no ingestion pipeline, no staleness window between an index
   update and reality), at the cost of search latency being bound by
   whichever source is slowest to respond. Given this project's actual
   scale (single operator, one community, not a multi-tenant SaaS with
   thousands of concurrent searches), that tradeoff is reasonable — revisit
   only if live fan-out proves too slow in practice, not preemptively.

**Net effect of these three answers: Phase 10 is larger than the minimal
reading of the original feature list would have suggested.** Worth
knowing going in, not discovering mid-build — this is now three real
subsystems (multi-source topology rendering, per-user dashboard
customization, federated search) on top of the full rewrite itself, not
one rewrite plus some polish.

## Phase 11 — Multi-Node Clustering & High Availability
**Component:** `umbrella-core` + `umbrella-daemon`, cluster-aware
*(full detail carried forward from v2's Phase 9 — scope expanded per v3's diff
column: auto-placement policies, resource prediction, and capacity forecasting are
new additions, not in the original v2 text)*

- Distributed node management, container scheduling across nodes (bin-packing by
  resource availability, not just "pick a node")
- Auto-placement policies, resource prediction, capacity forecasting, maintenance
  windows
- Core control-plane HA (no single point of failure for the API itself —
  active/standby or active/active depending on what the chosen deployment topology
  actually needs)
- Cluster awareness in the dashboard (fleet view, not just per-node — likely
  overlaps Phase 10's fleet overview, worth reconciling ownership between the two
  phases when Phase 10 gets its design pass)
- Assisted migration (Phase 4) extended to be scheduler-driven (e.g. draining a
  node for maintenance triggers migrations automatically)

**Definition of done:** a node can be drained for maintenance with its servers
automatically migrated elsewhere with bounded downtime, and core itself survives a
single-instance failure.

**Complexity flag:** of everything left in the roadmap, this is the phase most
likely to need extra design-discussion time before building, on the same order as
the event-bus/sandboxing decisions in Phase 7/8 — distributed consensus and
partition handling are a different, harder class of correctness problem than
anything built so far, and bugs here tend to be timing-dependent and silent rather
than caught by a straightforward test run.

## Phase 12 — Platform Maturity
**Component:** cross-cutting
*(full detail carried forward from v2's Phase 10, scope-corrected per v3's diff:
installer/updater's blue-green/canary language is explicitly scoped to
control-plane self-upgrade only, not individual Minecraft servers — see the
"Correcting scope" note below)*

- Installer + updater (self-update path for core/daemon/dashboard, with
  canary/rolling/blue-green rollout **scoped to the control-plane components
  themselves** — a running Minecraft world is a single stateful process, there's
  no meaningful "run two versions of the same world simultaneously" to canary
  between; the actual per-server equivalent is maintenance windows plus
  config-validation-before-rollout, which is Phase 11's job, not this phase's)
- Internationalization (dashboard + bot strings externalized, not retrofitted
  per-string later)
- Feature flags, configuration versioning (so a bad config change is diffable and
  revertible)
- Self-diagnostics/health-check endpoints platform-wide
- Multi-tenancy: the org-scoped data model from Phase 2 gets actual
  tenant-isolation implementation *if and when there's a real customer need* — not
  built speculatively before that
- CI/CD pipelines, test coverage targets enforced per domain, developer
  documentation (SDK, API reference) and user documentation (operator guides)

**Definition of done:** a fresh install can be stood up by the installer, updated
in place with a tested rollback path, and a new contributor can find API docs and
SDK docs without asking anyone.

---

## Summary table

| Phase | Theme | Status |
|---|---|---|
| 0 | Platform Contract | ✅ done |
| 1 | Daemon core, environment abstraction | ✅ done |
| 2 | Hosting control plane, event bus, audit log | ✅ done |
| 3 | Identity/RBAC/SSO/MFA, dashboard hosting UI | ✅ done |
| 4 | Files, backups, DR, scheduler, self-healing, secrets | ✅ done |
| 5 | AI operating-system layer | ✅ done |
| 6 | Discord + unified notification fabric | ✅ done |
| 7 | Developer Platform I — public API, SDKs, webhooks, Terraform | 🔶 in progress |
| 8 | Developer Platform II — plugin SDK, sandboxing, marketplace | 🔶 in progress |
| 9 | Observability & security hardening | ✅ done (corrected 2026-08-15 — independently confirmed twice, by two separate sub-chat sessions checking the actual code, not each other's word: WAF/metrics/rate-limit/tracing middleware, log aggregation with tests, a committed Grafana dashboard config, and a CVE scanner all real and present. See `PHASE-STATUS-CORRECTED.md` and `subchat-handback/task_c_phase_status_verdict.md`.) |
| 10 | Unified Experience Layer — **full dashboard rewrite, scope locked** | 🔶 substantially done (corrected 2026-08-15, same double-confirmation as above — steps 0–8 complete including the Settings page; marketplace listing/install UI still a placeholder, no manual browser testing done yet) |
| 11 | Multi-node clustering & HA — **highest remaining complexity** | ⬜ not started |
| 12 | Platform maturity | ⬜ not started |

Dependency spine: 0 → 1 → 2 → 3 is load-bearing — nothing works without the
contract, the daemon, the control plane, and identity, in that order. 4–6 build the
operator experience. 7–8 open the platform to developers. 9–10 make it observable
and pleasant to run at scale. 11–12 make it enterprise-durable.

## Flagged future ideas — not yet scoped into any phase above

Two real ideas surfaced in conversation that don't fit any existing phase's
definition and haven't had a real design pass. Capturing them here so they aren't
lost, not committing them to a phase number yet.

**Minecraft-server-side two-way communication (direct push, not just poll).**
Confirmed Sepiso Toni's ACLClouds plan supports extra port allocations, which changes
an earlier assumption — a genuine core-initiated direct connection to the
server's IP:port is buildable, not just the poll-based command-queue model.
Real pieces, none built yet:
- A new, lightweight server-registration model with `ip_address`/`port` fields —
  **not** the existing `models/hosting.py::Server` table, which is shaped around
  the daemon-managed lifecycle (`node_id`, `template_id`, `memory_bytes`,
  container status) that doesn't apply to a no-daemon, externally-hosted server.
  Bolting IP/port onto that table would leave it full of always-null
  daemon-only fields for this use case.
- A `connection_mode` setting (`push_preferred` / `poll_preferred` / `push_only`
  / `poll_only`) so core can try a direct connection first and fall back to the
  existing enqueue-and-poll path, or vice versa, per operator preference.
- The Minecraft plugin auto-updating its stored "core's address" when it
  receives a request from core, **gated strictly on the request passing the
  existing plugin-key auth check** — never on raw source-IP trust alone. This
  distinction matters: tying the update to "authenticated request received" is
  safe; tying it to "something connected from a new IP" is a real spoofing
  vector (anyone reachable on that port could redirect where the server sends
  its data without ever needing the key). Whoever builds this must not take
  the IP-trust shortcut.
- The existing heartbeat/poll loop should keep running as a baseline
  regardless of which `connection_mode` is active, so a broken direct
  connection degrades to the existing poll-based visibility rather than to
  silence.

**Plugin-authored Minecraft gameplay add-ons (marketplace → live server code).**
A materially bigger idea than anything else in Phase 7/8: installing a plugin
in the marketplace could push a JAR/code bundle to the live Minecraft server
and hot-load it, so a plugin can genuinely change server behavior (Sepiso Toni's
example: an ice-boat-racing gamemode that spawns/traps players) — and
uninstalling it reverts the change. Sepiso Toni's stated framing:
**it runs "under the authority of the original umbrella plugin, within it, not
out of it"** — i.e. loaded via the existing `UmbrellaPlugin` rather than
installed as an independent JAR. Worth being explicit that this framing is a
deployment/packaging choice, not a security boundary — Java gives no
per-loaded-code sandboxing equivalent to `ProcessSandbox`'s process isolation,
so code loaded this way still runs with the full trust of the JVM process
either way. Two very different projects depending on the answer to one
question, deliberately left open rather than assumed:
- **Sepiso Toni's own authored code only** — this is basically a deployment
  pipeline (push code, hot-load, remove later). Comparatively low risk,
  straightforward to design.
- **Third-party marketplace-published gameplay code** — this is a
  fundamentally bigger security question, on the order of what
  `services/plugins/sandbox.py` took to get right for Python, except Bukkit/the
  JVM doesn't offer an equivalent containment mechanism to build that
  confidence on. Would need a real constrained scripting/declarative layer
  (closer to the tiny-vocabulary pattern used everywhere else in this
  project) rather than raw JAR upload, and its own dedicated design session
  before any code gets written — the same discipline every other real
  decision in this project has gotten, not skipped because it's exciting.

Neither of these has a phase number yet. Revisit and scope properly when
picked back up — don't let "we discussed it once" turn into "so it's already
decided" the way roadmap assumptions have bitten this project before.

## Threat modeling — a practice, not a phase (carried forward from v3, unchanged)

"Assume internet-exposed, assume malicious users" shapes every phase's design, not
just Phase 9. From Phase 0 onward: every capability declares a required permission
(no implicit trust), every destructive/irreversible action is flagged at
declaration time, every file operation is daemon-enforced path-jailed (Phase 4),
every webhook payload is signed (Phase 7), every plugin runs sandboxed with
declared, reviewable grants (Phase 8), every API key is scoped and revocable
(Phase 0/3). Phase 9 is where the cross-cutting *infrastructure* for security (log
aggregation, anomaly/threat detection, hardening sweep) gets built — the discipline
runs the whole way through, and each phase's definition of done includes "what
could a malicious, authenticated-but-low-privilege user do here" as an explicit
check, not an afterthought.
