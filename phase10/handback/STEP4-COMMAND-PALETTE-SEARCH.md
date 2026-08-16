# Step 4 — Command palette + global search: manifest & handback

## Roadmap decision held exactly

`UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`, locked answer #3: "federated
into one search UI — via live fan-out per keystroke, not a pre-built
index." No search index, no ingestion pipeline, no staleness window —
every keystroke (debounced client-side to avoid firing on every single
character) triggers a real parallel fan-out against the live backend.
Latency is bound by the slowest source, which the roadmap doc accepts
explicitly given this project's actual scale.

## New files

```
lib/search-types.ts       — SearchResultItem shape
lib/search.ts              — source registry + runFederatedSearch (server-only)
app/api/search/route.ts    — same-origin route the client palette calls
components/command-palette/command-palette.tsx  — the palette itself
components/command-palette/search-trigger.tsx   — Topbar click affordance
```

Changed: `components/nav/topbar.tsx` (renders `SearchTrigger`),
`app/(dashboard)/layout.tsx` (mounts `CommandPalette` once for the whole
authenticated shell).

## Why the fan-out goes through a Next.js route, not straight from the browser

Every other backend call in this app keeps the session token server-side
(`lib/api.ts` is `server-only`, the token lives in an httpOnly cookie).
The command palette holds that invariant too: the browser only ever calls
same-origin `GET /api/search?q=`, which reads the httpOnly cookie server-
side and does the real fan-out from there. The bearer token never has to
exist in client-side JS just because search got interactive.

## Sources wired up, and why each one

Picked by scanning the actual registered capabilities
(`grep -rn '^    name="' capabilities/*.py`) for anything with a free-text
query param, then checking `required_permission` and `audited` on each:

| Source | Capability / endpoint | Gated by | Notes |
|---|---|---|---|
| Navigate | `lib/nav-config.ts` (no network call) | (matches what's already visible) | zero-cost, always first |
| Players | `GET /api/v1/players?username=` | `players.view` | pre-registry REST endpoint, not a capability — used directly |
| Knowledge base | `knowledge.entry.search` | `knowledge.entry.search` | `audited=False` |
| Logs | `platform.observability.search_logs` | `observability.logs.view` | `audited=False` |
| Marketplace | `marketplace.listing.list` | `marketplace.listing.view` | no server-side query param; filtered client-of-the-route-handler-side after a real fetch — still a live call every keystroke, just no backend filter to ask for. Fine at this project's actual catalog size; revisit only if that stops being true, not preemptively (same posture the roadmap doc takes elsewhere). |

Every source is gated by the caller's real permission (`user.permissions`
from the already-resolved `/auth/me` session) **before** it's called —
the palette never fires a request it already knows will 403, and never
shows an empty section from a source the user can't use in the first
place.

## A real exclusion, not an oversight: `archive.search`

`capabilities/archive_search.py` sets `audited=True` specifically because
it "reveals unfiltered chat content" — that's the one search-shaped
capability in the whole registry with an audit trail attached. Firing it
on every keystroke of a live fan-out would write an audit-log entry for
every partial, not-yet-finished search string a staff member types —
noisy at best, a real audit-log-pollution problem at worst (someone
reviewing the audit log later sees a fake trail of a dozen near-identical
"searches" that were really just one person typing one query). Left out
of `SOURCES` entirely, with the reasoning inline in `lib/search.ts` as a
comment. Archive search belongs behind an explicit submit action (a
"press Enter to search chat archive" affordance, presumably its own
future page or a palette mode-switch), not live fan-out — not built in
this step; flagging it here so it isn't silently forgotten as scope.

`platform.audit.search` was also considered and left out for a related
but different reason: its params are `actor_type`/`action` exact-match
filters, no free-text `query` field at all — not a natural fit for a
text search box without inventing a param mapping the capability doesn't
actually support.

## Independent per-source failure, same posture as step 3's widgets

`runFederatedSearch` catches each source's `run()` independently — one
source erroring (a backend hiccup, an unexpected shape) drops that
source's section from the results, never the whole palette. Same pattern
`lib/widgets.ts::fetchWidgetData` already established in step 3, applied
here for the same reason.

## What is NOT independently verified, same caveat as steps 2 and 3

Still no network access in this sandbox. This step adds real client-side
interactivity (keyboard handling, debounce, an abort-stale-response
guard via a monotonically increasing request id) that's higher-risk to
ship unverified than step 3's server components were — `npm run build`
and manual keyboard-interaction testing both need to happen in an
environment with registry access before this is trusted as done.
