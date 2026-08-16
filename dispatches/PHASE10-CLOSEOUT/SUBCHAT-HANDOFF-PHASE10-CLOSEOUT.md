# UmbrellaOS — Sub-chat dispatch: Phase 10's last 2 widgets (activity timeline + fleet overview)

Read this, then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`, then
`MASTER-PROJECT-STATUS-AND-HANDOFF.md`. **Session label:
`subchat-phase10-closeout`.**

Phase 10's original locked scope (`phase10/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`,
line ~135) named 8 things. 6 are built and verified — see
`phase10/handback/` for all of them. **Two were never built and nobody
flagged it: activity timeline, fleet overview.** This dispatch is those
two, nothing else.

## Why these two specifically, and why they're small

Every other item on the list needed new plumbing. These two don't — the
data already exists as real, tested capabilities:
- **Activity timeline** ← `platform.audit.search`
  (`capabilities/system.py`): paginated, filterable
  (`actor_type`, `action`) audit log. `AuditEntryResult`: `id`, `actor`,
  `actor_type`, `action`, `target`, `details`, `created_at`.
- **Fleet overview** ← `hosting.server.list` (`capabilities/hosting.py`):
  every server across every node. Also look at `hosting.node.list` and
  `hosting.server.stats` — read the full file before deciding whether
  fleet overview should show servers only, or servers grouped by node
  with per-node health.

This is a UI-only dispatch. Don't add backend capabilities — if you find
yourself wanting to, stop and flag it instead (rule 2.2), the two
capabilities above should be sufficient for a real v1 of both.

## Task — build both as real dashboard content

Both are Tier-1-shaped (the existing `stat_pair`/`status_badge`/`simple_list`
rendering model from `STEP3-TIER1-WIDGETS.md` and
`components/widgets/plugin-widget.tsx`) — but these are **first-party**
widgets, not plugin-supplied ones, so they don't go through the
`marketplace.install.dashboard_slots` plugin-widget pipeline. Build them
as their own components following that pipeline's *conventions*
(trusted-component rendering, no raw HTML from capability results) without
routing through the plugin-slot machinery meant for third-party data.

1. **Activity timeline** — a widget/section (your call: dashboard page
   addition, or its own route — check `lib/nav-config.ts` and decide
   what fits, state your reasoning) showing recent audit entries,
   human-readable (`actor` + `action` + `target`, relative timestamp from
   `created_at`), paginated via `platform.audit.search`'s existing
   `limit`/`offset`. Permission-gate on `audit.view` (the capability's
   own `required_permission`) the same way `settings/page.tsx` and
   `marketplace/page.tsx` already gate on their respective permissions —
   read both before building, they're your two most recent examples of
   this exact pattern.
2. **Fleet overview** — a widget/section showing servers (and their
   node), status, and whatever `hosting.server.stats` gives you that's
   worth surfacing at a glance (don't overbuild — this is an overview,
   not the full hosting console; link out to per-server detail only if a
   real route for that already exists, don't invent one). Permission-gate
   on `hosting.server.view`.
3. Both are server components fetching data server-side (same
   catch-and-degrade-to-empty posture as every other list fetch in this
   app), with at most one `'use client'` leaf each if genuinely
   interactive (e.g. a refresh button, a filter) — most of this doesn't
   need to be interactive at all.

## Verification

Standard loop, both sides: fresh venv + `pytest` (backend shouldn't
change, so this should stay at 844/844 — if it doesn't, something's
wrong), fresh `npm install` + `tsc --noEmit` + `lint` + `build`, all run
for real. Leak-check before every commit (`find . -iname ".env" -o
-iname "*.db" -o -iname "*.sqlite*"`), not just before handback.

## What to hand back

A handback doc (model: `phase10/handback/STEP9-MARKETPLACE-UI-AND-FIRST-TEST-PASS.md`),
plus a real diff. Commit under `subchat-phase10-closeout` (this project
uses real git now — clone with the read-only token you were given,
you cannot push, package your commit's diff for handback same as always).
