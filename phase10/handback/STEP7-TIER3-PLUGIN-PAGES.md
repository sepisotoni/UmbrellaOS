# Step 7 (Tier 3 only) — Plugin-owned pages

Tier 2 (config toggles) is **not** in this handback — still explicitly
blocked on Sepiso Toni's sign-off on Decision 2, per the kickoff doc's own
instructions. This covers Tier 3 (`app/marketplace/[pluginId]`) only,
which the kickoff doc's own step 7 description notes doesn't depend on
that sign-off.

## What "opt-in" means here, end to end

Per `DASHBOARD-PLUGIN-UI-SCOPING.md`'s Tier 3 section: no page declared
in a plugin's manifest means no sidebar entry, no placeholder route
content, nothing rendered. This holds at every layer:

- **Manifest**: `page: PageDecl | None = None` — omitting it is the
  default, not a degenerate case.
- **Service**: `MarketplaceService.pages()` only returns entries for
  plugins that declared one; `page_layout()` 404s (via
  `ResourceNotFoundException`) for both "not installed" and "installed,
  no page" — the same response either way, since both mean "nothing to
  show" to a caller.
- **Sidebar**: only fetches `marketplace.install.pages` at all if the
  caller holds `marketplace.install.view`; renders a "Plugins" section
  only if the result is non-empty.
- **Route**: `fetchPageLayout` turns a 404/403 into `null`, and the page
  component renders a plain "not installed / no page" message for that
  case — not a broken page, not a silently-empty grid that looks like a
  loading bug.

## Backend (`umbrella-core`)

`PageWidgetDecl` / `PageDecl` on the manifest side, `PageWidgetEntry` /
`PageNavEntry` / `PageLayoutEntry` + `MarketplaceService.pages()` /
`.page_layout()` on the service side, `marketplace.install.pages` /
`marketplace.install.page_layout` as the two new capabilities. Full
detail and design-decision notes in
`umbrella-core-step7-tier3-changes/MANIFEST-STEP7-TIER3-CORE.md`.

**Verified independently**: fresh venv, offline install from the kickoff
package's wheels, real `pytest` run. 798 → 819 passed (21 new tests), not
a self-report.

One real schema decision worth restating here since it's the one place
Tier 3 genuinely diverges from Tier 1: `render_as` on a page widget
accepts `"table"`, which Tier 1's `dashboard_ui_slots[].render_as` still
rejects — the manifest schema itself enforces this per-tier, so a plugin
can't accidentally declare a table-shaped dashboard widget that the
Tier 1 dispatcher would silently drop.

## Frontend (`umbrella-dashboard`)

- `lib/types.ts` — added `PageWidget` / `PageNav` / `PageLayout`,
  mirroring the new capability result shapes exactly.
- `lib/marketplace-pages.ts` (new) — `fetchPluginNavEntries` (catches
  failures → `[]`, same posture as `lib/widgets.ts::fetchSlots`),
  `fetchPageLayout` (catches 404/403 → `null`, but re-throws anything
  else — a genuine backend outage shouldn't get silently folded into the
  same "nothing here" message as a legitimate opt-out), and
  `resolvePageWidgets` (same per-widget independent-failure isolation as
  Tier 1's `resolveSlotWidgets`).
- `components/widgets/table-widget.tsx` (new) — the fourth trusted
  renderer. Columns are derived from the union of the actual row keys in
  declared order, never a plugin-supplied column list — same
  no-plugin-supplied-structure stance the other three renderers hold, now
  extended to column headers, not just cell values.
- `components/widgets/plugin-widget.tsx` — the dispatcher's `decl` prop
  is now the minimal structural type `{ label, render_as }` instead of
  importing `DashboardSlot` by name, so both Tier 1 slots and Tier 3 page
  widgets can share the one dispatcher (Decision 1: one rendering model
  for every tier) rather than Tier 3 needing a parallel copy. `"table"`
  is genuinely reachable now.
- `lib/nav-icons.ts` (new) — a fixed lookup table from the manifest's
  curated `nav_icon` strings to real `lucide-react` components.
  Deliberately a lookup table, not a dynamic import by name, so a
  plugin's icon string can only ever resolve to something already
  reviewed and bundled, not reach into the icon package arbitrarily.
- `components/nav/sidebar.tsx` — fetches `marketplace.install.pages`
  (gated behind the caller already holding `marketplace.install.view`,
  same permission the static "Marketplace" nav item requires) and renders
  a "Plugins" section of links, each with its resolved icon, only when
  there's at least one entry.
- `app/(dashboard)/marketplace/[pluginId]/page.tsx` — replaced the step-2
  placeholder. The one generic dynamic route per Decision 5: fetches the
  plugin's layout server-side, resolves each widget's live data
  independently, and renders through `PluginWidget`. Not one file per
  plugin.

**Verified independently this session** — the same real build/lint
discipline step 6 established (the first step to have working npm
registry access):

```
npm install
npm run build
```

Result: clean Turbopack build, `/marketplace/[pluginId]` shows up as a
dynamic (`ƒ`) route alongside the rest of the shell, zero TypeScript
errors. Not run through `eslint` — **this scaffold has never actually
shipped an `eslint.config.js`** despite step 6's handback describing an
eslint pass; re-checked the actual step 6 deliverable zip this session
and confirmed the config file itself was never in it. Flagging as a
pre-existing gap rather than silently working around it — worth adding a
real eslint config in a future step, not invented ad hoc here since
that's a scaffold-level decision, not a Tier 3 one.

Also worth flagging plainly, unrelated to this step's own changes:
`npm install` surfaced `next@16.0.1: This version has a security
vulnerability. Please upgrade to a patched version (CVE-2025-66478)` —
pre-existing from step 2's scaffold, not something this step introduced
or fixed. Same "call it out, don't quietly patch scope I wasn't asked to
touch" posture as step 6's tailwind-mismatch note.

## What's left after this

- **Tier 2 config toggles** — still blocked on Sepiso Toni's Decision 2
  sign-off, not attempted.
- **Marketplace listing/install UI** (`app/marketplace/page.tsx` itself)
  — never actually in scope for any of steps 0–7's breakdown; still the
  step-2 placeholder. Worth its own explicit ask if wanted, not assumed
  into this step.
- The `next@16.0.1` CVE and the missing `eslint.config.js`, both flagged
  above, neither fixed here.
