# Phase 10 — Unified Experience Layer: Build-Kickoff Handoff

Read this completely before writing any code. This is a **from-scratch
rewrite of `umbrella-dashboard`**, not an extension of the existing one —
confirmed, not up for re-litigation. See
`roadmap-and-design-docs/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`'s
Phase 10 section and `DASHBOARD-PLUGIN-UI-SCOPING.md` for the full reasoning
history; this doc is the actionable summary plus the decisions that were
still open as of the last head-chat session, now closed.

## Why a full rewrite, not an extension

The current `umbrella-dashboard` descends directly from the pre-rebuild
`UmbrellaMC` prototype — used as a literal starting point at Phase 3, never
touched since while the backend evolved underneath it across five more
phases. It also has 26 of 27 pages marked `'use client'`, which is the
likely cause of load-time complaints (everything waterfalls from
browser-side JS instead of Next.js 16's server-rendering default). Phase
10's own feature list (command palette, topology, custom dashboards) was
never going to retrofit cleanly onto that foundation either. So: one
rewrite, not two.

**Confirmed constraint: no v0 or external mockup tooling.** Build directly
against the real backend — real capability registry, real RBAC role
ladder, real API shapes from `umbrella-core-PHASE9-COMPLETE.zip` (now
Phase-9-follow-up-patched — CVE fixes + OTel SDK swap independently
verified, 783/783). The old dashboard source
(`original-daemon-and-dashboard/umbrella-dashboard-FULL.zip`) is reference
material for what NOT to repeat, not a starting point — don't copy files
forward.

## Scope (from the roadmap doc — unchanged)

Command palette, global search, activity timeline, live topology map,
dependency graph, fleet overview, custom dashboards/widgets, workspace
layouts, plus the three-tier plugin UI model below.

## Decisions — all now closed

### 1. Rendering model across all three plugin-UI tiers — LOCKED
Schema-driven only. A plugin declares its shape from a small vocabulary
(stat pair / status badge / simple list / table); the dashboard's own
trusted components do the actual rendering. **No plugin-supplied
JSX/JS ever runs in the browser** — same trust-boundary reasoning as
`ProcessSandbox`, except a browser has none of `ProcessSandbox`'s
isolation guarantees, so this is not negotiable.

### 2. Config-write capability shape (Tier 2 toggles) — OPEN BY DESIGN, propose both
Sepiso Toni's call: **don't silently pick one — implement both option shapes
as a real proposal, then stop and ask for the decision before wiring
either one in as the final path.**
- **(A) Per-plugin auto-generated**: `plugin.<plugin_id>.config.set`,
  narrow permission scope per plugin, more capabilities registered overall.
- **(B) One generic capability**: `marketplace.install.config.set(plugin_id,
  key, value)`, one broad "can write any installed plugin's config"
  permission.

Write up the concrete schema/permission-model diff between A and B (what
gets registered in the capability registry, what an RBAC role grant looks
like for each, what an audit-log entry looks like for each) as a short
comparison in the handback doc. Do not build the dashboard-side toggle UI
against whichever one you pick without that comparison being reviewed
first — this is a real permission-model fork, not a style preference.

### 3. Toggle propagation timing — LOCKED
Default: "next poll cycle" (a sandboxed plugin has no persistent running
instance — `ProcessSandbox` runs fresh per invocation, so a toggle takes
effect on the plugin's next poll/cog-check, not instantaneously).
Instant-reaction via `EventBus.publish()` is a per-toggle opt-in a plugin
author explicitly requests in the manifest, never a platform-wide
guarantee.

### 4. New route name — LOCKED
`app/marketplace`, not `app/plugins`. `app/plugins/page.tsx` and the
`Plugin` TS type already mean Bukkit/Paper server-side plugins
(heartbeat/TPS/status) — a different concept that happens to share a
word. Don't conflate them.

### 5. Page-layout route strategy (Tier 3) — LOCKED
One generic dynamic route, `app/marketplace/[pluginId]/page.tsx`,
fetching the plugin's declared page layout and rendering it generically.
Not one hand-written `.tsx` file per plugin — that would mean a dashboard
code change on every plugin install.

### 6. `'use client'` usage — LOCKED
Scope to genuinely interactive leaf components only (a toggle switch, a
live-polling stat). Default to server components everywhere else. This
is the fix for the load-time problem described above — don't reintroduce
it in new code.

### 7. `render_as` field (Tier 1 widget-shape signal) — LOCKED, confirmed real gap
`DashboardSlotDecl` (`services/plugins/manifest.py`) and
`DashboardSlotResult` (`services/plugins/marketplace.py`) currently only
carry `slot`/`label`/`capability` — nothing signals which widget shape
(stat pair / status badge / simple list) a slot should render as.
**Add `render_as: Literal["stat_pair", "status_badge", "simple_list"]`
to `DashboardSlotDecl`** (and `"table"` once Tier 3 needs it), following
the exact tiny-vocabulary pattern already used by `_ALLOWED_FIELD_TYPES`.
Keep shape-based inference as a fallback for plugins that don't declare
it (array → list; object with a lone `status` string → badge; otherwise
every top-level scalar → one stat-pair entry) — `render_as` is the
reliable path, inference is graceful degradation, not the other way
around.

### 8. Marketplace response-shape verification — NOT pre-captured, verify live as step zero
A prior session was mid-flight building Tier-1 widgets against the old
(pre-rewrite) dashboard when the rewrite decision landed. Its findings on
whether `marketplace.install.list` / `marketplace.install.dashboard_slots`'s
**real** response shape matched what the scoping doc assumed were never
captured before that session stopped — checked the full handoff package,
not there. **Do not assume the scoping doc's API-shape assumptions are
verified.** Before building any Tier-1 widget rendering: call those two
capabilities for real against the patched `umbrella-core`, diff the
actual response against what `DASHBOARD-PLUGIN-UI-SCOPING.md` assumed, and
note any mismatch in your handback doc.

## Sequencing — core schema first, then dashboard

`services/plugins/manifest.py` and `services/plugins/marketplace.py` need
the `render_as` field (Decision 7) and, once Decision 2 is resolved, the
config-write capability, before dashboard UI can build against real
shapes. **Do the core-side schema extension first**, as its own
diff+manifest against `umbrella-core-PHASE9-COMPLETE.zip` (patched), with
its own test coverage, verified independently before dashboard work
starts consuming it — same discipline as every other phase, not skipped
because this is "just a dashboard phase."

## What "done" looks like for this dispatch

This is large enough that it should not be one single build-and-return.
Suggested breakdown, each independently verifiable:
1. Core schema extension: `render_as` field + Decision 2 comparison
   writeup (not final implementation of whichever option — that needs
   Sepiso Toni's sign-off first).
2. Dashboard scaffold: Next.js 16 app shell, server-component-by-default
   layout, auth wired to the real RBAC role ladder, no page content yet.
3. Tier 1 widgets (`app/dashboard` widget rendering) — after step 0's
   live-shape verification.
4. Command palette + global search (federated live fan-out per keystroke,
   per the roadmap's locked answer — no pre-built index).
5. Topology map (two toggleable layers: infra from Phase 2, capability
   dependency graph from Phase 8 — switchable views over one canvas, not
   one mixed graph).
6. Custom per-page dashboards: `(user_id, page_id, layout_json)`
   persistence model. **Explicitly enumerate which pages are
   customizable** — not "all of them" — and design a real default
   widget arrangement per customizable page, not a placeholder.
7. Tier 2 config toggles (after Decision 2 is actually resolved with
   Sepiso Toni) + Tier 3 plugin-owned pages (`app/marketplace/[pluginId]`).

Each of these should come back as its own diff+manifest against a clean
baseline, independently re-verified (fresh venv/fresh `npm ci`, real test
run, not trusting the build session's self-report) before being folded
into the next step — same discipline that's held for every phase so far.

## Reference material in this package

- `roadmap-and-design-docs/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md` —
  Phase 10 section, full context
- `DASHBOARD-PLUGIN-UI-SCOPING.md` — full original reasoning behind every
  decision above
- `umbrella-core-PHASE9-COMPLETE.zip` — apply the Phase 9 follow-up patch
  (CVE fixes + OTel SDK swap, `MANIFEST (2).md` / `MODIFIED_FILES (2).diff`
  from the last head-chat session) before treating this as current
- `original-daemon-and-dashboard/umbrella-dashboard-FULL.zip` — old
  dashboard, reference-only, do not use as a starting point
