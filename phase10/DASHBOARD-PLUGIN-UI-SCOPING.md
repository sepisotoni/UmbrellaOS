# UmbrellaOS — Dashboard Plugin UI: Scoping Doc

This is a design-decisions doc, not a build handoff — read this, make the
calls explicit (or confirm the defaults below), *then* write the actual
build handoff before any dashboard code gets touched. Same discipline as
the event bus / plugin storage / marketplace decisions: state the design
before building it.

**Repos involved:** `umbrella-core` (manifest schema extension — new work,
not yet built) and `umbrella-dashboard` (consumes it — also new work).
Sequencing: core's schema extension has to land first; dashboard can't
build UI against a shape that doesn't exist yet.

## The three tiers, in increasing order of scope

### Tier 1 — Widgets (`dashboard.widgets` slot) — schema already exists today

`services/plugins/manifest.py` already has a `dashboard_ui_slots` field with
three allowed slot values: `sidebar.tools`, `sidebar.moderation`,
`dashboard.widgets`. This is the smallest tier — a plugin's widget renders
readonly data (like your status-channel plugin's online/player-count/TPS)
inside a dashboard-owned container. **No core changes needed for this
tier** — it's the same mechanism `discord_commands` used before the Discord
session wired it up: declared in the manifest, validated at registration,
just not yet consumed by any dashboard code.

**Rendering model (the fork flagged earlier, worth locking in now):**
schema-driven, not plugin-supplied markup. A widget declares its shape from
a small vocabulary — stat pair, status badge, simple list — and the
dashboard's own trusted components (`components/ui/card.tsx`,
`components/dashboard/stat-card.tsx`) do the actual rendering, including
any animation (value-change transitions, etc., using existing libraries
like `recharts`, already a dependency). The plugin never supplies its own
JSX/JS that runs in the browser — that would reopen the exact trust-boundary
question `ProcessSandbox` was built to answer, but in a browser context
where none of those guarantees (process isolation, resource limits) apply.
**Recommendation: lock this in as the model for all three tiers, not just
widgets** — consistent with every other Phase 7/8 decision (tiny param
vocabulary, no plugin imports), and it's the only model where a plugin genuinely
can't do anything sketchy through the dashboard.

### Tier 2 — Config toggles — new, needs a core schema addition

Plugin declares simple settings (starting scope: booleans/toggles only —
text/number fields are a natural follow-on if a real plugin needs them,
don't build them speculatively) that render inline in the existing Settings
page, not a new route.

**What core needs to add** (not built yet):
- A new manifest field, e.g. `config_fields: list[ConfigFieldDecl]`, each
  with `key`, `type` (start with just `"boolean"`), `label`,
  `default_value`. Same tiny-vocabulary pattern as `_ALLOWED_FIELD_TYPES`.
- A **write path**, not just a read one. This is the part that doesn't
  exist yet at all: a toggle flip needs a capability that writes the new
  value into the plugin's own `kv` storage (Decision 2 from Part 1) —
  something like an auto-generated `plugin.<plugin_id>.config.set` alongside
  whatever the plugin author declares themselves, or a generic
  `marketplace.install.config.set` capability parameterized by plugin_id +
  key. **Decide which of these two shapes before building** — auto-generated
  per-plugin vs. one generic capability is a real fork with different
  permission-model implications (per-plugin write, or one broad "write
  installed plugin config" permission).

**The propagation-timing nuance already discussed:** a sandboxed plugin has
no persistent running instance — `ProcessSandbox` runs a plugin's function
fresh per invocation. A toggle takes effect on the plugin's *next*
invocation (next poll cycle, next Discord-cog check), not instantaneously.
If a specific toggle genuinely needs to take effect immediately, that
requires the write to also `EventBus.publish()` a notification — real added
complexity, only worth it for a toggle that actually needs it, not a
default. **Recommendation: "next poll cycle" is the default; treat
instant-reaction as a per-toggle opt-in a plugin author explicitly requests,
not a platform-wide guarantee.**

### Tier 3 — Plugin-owned pages — new, needs a bigger core schema addition

A plugin gets its own route and its own sidebar nav entry — for cases like
an inventory-status table that genuinely doesn't fit a small widget card.
**Strictly opt-in per plugin** — no page declared in the manifest means no
sidebar entry, no placeholder, nothing rendered. This was explicitly
confirmed as the right default, not just a nice-to-have.

**What core needs to add** (not built yet):
- A manifest section describing a whole page's layout — realistically a
  list of the same widget vocabulary from Tier 1 (stat/badge/list), plus a
  **new type this tier needs that Tier 1 doesn't**: `table`, since an
  inventory-status view is exactly the case a stat card can't represent.
  Still schema-driven, still no plugin-supplied markup — same trust
  boundary reasoning as Tier 1, just a richer vocabulary.
- Nav metadata: a label and an icon reference (from the existing
  `lucide-react` set already used throughout the dashboard, not a
  plugin-supplied icon asset — keeps this consistent with Tier 1's
  no-plugin-assets stance).
- A route registration mechanism — likely a single dynamic route like
  `app/marketplace/[pluginId]/page.tsx` that fetches the plugin's declared
  page layout and renders it generically, rather than one hand-written
  `.tsx` file per plugin. This is what keeps the dashboard from needing a
  code change every time someone installs a new plugin.

## Naming collision — resolve before any route gets created

`app/plugins/page.tsx` already exists and means something unrelated:
Bukkit/Paper **server-side** plugins reporting heartbeat/TPS/status (the
`Plugin` TypeScript type in `lib/types.ts` is already taken by this
concept). The new marketplace/sandboxed-plugin system needs its own,
differently-named route — **`app/marketplace`**, not `app/plugins` — to
avoid conflating two unrelated systems that happen to share a word.

## Performance constraint, carried forward from the earlier discussion

The existing dashboard has 26 of 27 pages marked `'use client'` — likely
the real cause of the "took long to load" feeling (everything waterfalls
from browser-side JS execution instead of the server sending mostly-finished
HTML, which is Next.js 16's default unless you opt out with `'use client'`).
**Constraint for all new work in this scoping doc:** keep `'use client'`
scoped to genuinely interactive leaf components (a toggle switch, a
live-polling stat) — not whole pages by default. This doesn't retrofit the
existing 26 pages (separate decision, not in scope here), but nothing new
should inherit the pattern.

## Summary of decisions to lock in before building (or confirm the
recommended default)

| # | Decision | Recommended default |
|---|---|---|
| 1 | Rendering model across all 3 tiers | Schema-driven only, no plugin-supplied markup — locked in, not really optional given the trust boundary |
| 2 | Config-write capability shape | **Undecided — needs an explicit call**: per-plugin auto-generated write capability, or one generic parameterized capability |
| 3 | Toggle propagation timing | "Next poll cycle" by default; instant-reaction via event-bus publish only as an explicit per-toggle opt-in |
| 4 | New route name | `app/marketplace`, not `app/plugins` |
| 5 | Page-layout route strategy | One generic dynamic route (`app/marketplace/[pluginId]`) rendering from declared layout data, not one file per plugin |
| 6 | `'use client'` usage in new code | Scoped to leaf interactive components only |
| 7 | **Widget-shape signal (confirmed real gap, not hypothetical)** | **Undecided — needs an explicit call**: see below |

Decisions 2 and 7 are the two real open forks left — everything else here
has a clear recommendation. Worth answering both explicitly before Phase 10
gets a build prompt.

## Confirmed gap: no widget-shape signal in the discovery schema

A Tier-1 build attempt against the pre-rewrite dashboard (since superseded
by the Phase 10 full-rewrite decision, but this specific finding survives
that) confirmed something the original version of this doc didn't
anticipate: `DashboardSlotDecl` (`manifest.py`) and `DashboardSlotResult`
(`marketplace.py`, what `marketplace.install.dashboard_slots` actually
returns) only carry `slot`/`label`/`capability` — **nothing says which of
the tier-1 widget shapes (stat pair / status badge / simple list) a given
slot should render as.** `PluginCapability.result`'s generic
`dict[str, ParamField]` schema isn't exposed through either discovery
capability, so there's no schema-level signal to key off even indirectly.

**Recommended fix, to build into whatever manifest schema Phase 10 (or a
core-side session ahead of it) implements:** add a `render_as` field to
`DashboardSlotDecl` — `"stat_pair" | "status_badge" | "simple_list"` (and
`"table"` once Tier 3 needs it) — following the exact tiny-vocabulary
pattern already established by `_ALLOWED_FIELD_TYPES`. A plugin author
declares the shape once in the manifest; the dashboard doesn't have to
infer it from whatever JSON happens to come back.

**Fallback worth keeping even after `render_as` exists:** shape-based
inference for plugins that don't declare it (array → list; object with a
lone `status` string → badge; otherwise every top-level scalar field →
one stat-pair entry — this is what makes the "online/players/tps" example
from earlier work with zero plugin-author effort). Treat `render_as` as
the reliable path and inference as graceful degradation, not the other
way around.

