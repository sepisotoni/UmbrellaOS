# Step 6 — Custom per-page dashboards

## What this delivers

Per-user, per-page widget layout customization: reorder dashboard widgets
and hide/show them, saved server-side, persisting across sessions. This is
the `(user_id, page_id, layout_json)` persistence model the kickoff doc
asked for (item 6), plus the explicit page enumeration + real default
arrangement it required instead of a placeholder.

## Which pages are customizable — explicitly enumerated, not "all of them"

One page today: **`dashboard`**. See
`umbrella-core/services/dashboard_layout/pages.py::CUSTOMIZABLE_PAGES` — a
registry, not a hardcoded literal scattered across files, so a future
customizable page (e.g. a Tier 3 plugin page once step 7 builds one) is one
new entry there, not a signature change everywhere `page_id` is checked.

Walked the actual route set from step 5's `nav-config.ts` to decide this:

- **`/dashboard`** — fed by the real `dashboard.widgets` Tier 1 slot
  (`marketplace.install.dashboard_slots`). Concrete, discrete, per-plugin
  cards. This is the one page "layout" means something for.
- **`/marketplace`** — a listing/install table, not widget-fed. Nothing to
  reorder.
- **`/topology`** — step 5's two-layer canvas. Its "layout" is the
  infra/dependency toggle, which is already client-side view state, not a
  set of discrete cards. Forcing it into this model would mean inventing a
  widget concept that page doesn't have.

## Default arrangement

Documented in the same registry entry: no saved layout means "whatever
order `marketplace.install.dashboard_slots` returns today (plugin
registration order), everything visible." Step 6 doesn't change that
default — it only adds the ability to override it per user. This was
already exactly what step 3 rendered before this step existed, so nothing
about the no-customization experience changes.

## Backend (`umbrella-core`)

- `models/dashboard_layout.py` — `DashboardLayout(user_id, page_id,
  layout_json)`, unique on `(user_id, page_id)` — a save replaces, it
  doesn't accumulate history. `layout_json` is a JSON-encoded
  `list[{widget_key, visible}]`, Text column, matching `Setting.value`'s
  existing JSON-ish-column convention rather than introducing a new one.
- `services/dashboard_layout/pages.py` — the `CUSTOMIZABLE_PAGES`
  allow-list described above.
- `services/dashboard_layout/service.py` — plain CRUD (get / upsert-set /
  delete-reset), no registry knowledge, mirroring
  `services/webhooks/service.py`'s split.
- `capabilities/dashboard_layout.py` — `dashboard.layout.get` / `.set` /
  `.reset`. Deliberately copies `capabilities/identity.py`'s
  `identity.mfa.*` shape exactly: always acts on the calling staff
  member's own row (no target-user param), `required_permission=None`
  (self-scoped preference data, not an elevated grant), and the
  admin-key/superuser tier is rejected with the same `_current_staff_user`
  pattern MFA uses — there's no underlying `User` row for a personal
  layout to attach to. `page_id` is checked against
  `CUSTOMIZABLE_PAGES` at this layer (400 if not customizable), not at the
  model layer, same separation `Setting.key` already keeps.
- `alembic/versions/026_dashboard_layouts.py` — new table migration.
- Registered in `capabilities/__init__.py`.

### Verified independently

Fresh venv, offline install from `wheels/` against the pinned
requirements (`pip install --no-index --find-links=wheels/ ...`), then a
real `pytest -q` run — **798 passed** (790 baseline + 8 new tests in
`tests/registry/test_capabilities_dashboard_layout.py`: round-trip,
replace-not-duplicate on a second save, reset, reset-as-no-op, per-user
isolation, bad-`page_id` rejection, admin-key rejection). Not a
self-report — this session ran it.

## Frontend (`umbrella-dashboard`)

- `lib/types.ts` — `LayoutWidgetEntry`, `DashboardLayoutResult`,
  `CustomizablePageId`, mirroring the capability's real shapes.
- `lib/dashboard-layout.ts` — `fetchLayout` / `saveLayout` / `resetLayout`
  (server-only, same `invokeCapability` path every other domain uses), and
  `applyLayout(liveWidgets, savedLayout)` — the actual merge logic:
  - A widget with a saved entry: kept in the saved order, shown/hidden per
    the saved `visible` flag.
  - A widget with **no** saved entry (a plugin installed after the layout
    was last saved, or nothing customized yet) is appended after the
    customized ones, in the page's live default order, always visible.
    This matters: a saved layout only ever stores what was explicitly
    customized, never a full snapshot, so installing a new plugin can
    never silently hide its widget forever.
  - A saved entry whose `widget_key` no longer matches any live widget
    (the plugin was uninstalled) is dropped — nothing to render for it.
- `app/api/dashboard-layout/route.ts` — same-origin `POST` (save) /
  `DELETE` (reset) route, same token-stays-server-side pattern as step 4's
  `/api/search` route. The browser never calls `umbrella-core` directly or
  holds the bearer token.
- `components/widgets/widget-grid.tsx` — now resolves the saved layout
  server-side before rendering (`applyLayout`), and mounts the customizer.
  Still a server component — layout *resolution* is a data concern, not an
  interaction, so it doesn't need to run in the browser (Decision 6).
- `components/widgets/dashboard-customizer.tsx` — the **one** `'use
  client'` leaf this step adds (Decision 6: scope client components to
  genuinely interactive leaves, same rule step 4's command palette
  followed). Plain up/down buttons + a visibility checkbox, not a
  drag-and-drop library — no new npm dependency to justify for a small,
  fixed widget count, same call step 5 made for the topology canvas.
  Receives only `{widget_key, label, visible}` per widget as props, never
  the plugin's actual data — the no-plugin-data-reaches-untrusted-code
  boundary (Decision 1) extends to the ordering UI, not just the widget
  renderers.

### Verified independently — first real build this project has had

Every step 0–5 handback flagged the same open item: no `npm ci`/build/lint
had actually been run, because a prior session's sandbox couldn't reach
the npm registry. That blocker is gone in this session — `npm install`
and `npx next build` both succeeded against the real registry.

Running the real build surfaced two genuine, pre-existing issues, both
fixed here rather than glossed over:

1. **A real TypeScript bug in this step's own new code** —
   `dashboard-customizer.tsx`'s reorder/toggle logic indexed into the
   widgets array without narrowing `undefined`
   (`noUncheckedIndexedAccess` is on in this project's `tsconfig.json`,
   correctly). `npx tsc --noEmit` caught it; fixed by narrowing before
   use. This is exactly the kind of bug "no build was ever run" was
   hiding — worth being explicit that it was real, not hypothetical.
2. **A pre-existing dependency mismatch from step 2's scaffold**:
   `package.json` pinned `tailwindcss@4.0.0` and
   `@tailwindcss/postcss@4.0.0`, but `@tailwindcss/postcss@4.0.0`
   transitively pulls in `@tailwindcss/node@4.3.3` → `tailwindcss@4.3.3`,
   so two different `tailwindcss` versions ended up in the tree and the
   build failed on `app/globals.css` with `Missing field 'negated' on
   ScannerOptions.sources` — a version-skew error, not anything to do with
   this step's widget/layout code. Fixed by bumping both packages to
   `4.3.3` (`npm install tailwindcss@4.3.3 @tailwindcss/postcss@4.3.3
   --save-exact`), which dedupes cleanly. `npx next build` also
   auto-corrected `tsconfig.json`'s `jsx` setting from `"preserve"` to
   `"react-jsx"`, flagged as a "mandatory change" for this Next.js/React
   version — left that correction in place since the build requires it.

After both fixes: `npx tsc --noEmit` is clean, and `npx next build`
completes cleanly (Turbopack, all 12 routes compiled, static pages
generated). This is the first time in this project's Phase 10 history
that an actual build has been run and passed — steps 2–5 built against
type-level and manual review only.

`npx eslint .` currently fails immediately with "couldn't find an
eslint.config.js" — the step 2 scaffold's `package.json` has an `eslint`
devDependency and a `lint` script but no ESLint v9 flat-config file was
ever added. Left as-is (out of scope for this step to invent lint rules
for the whole project), but flagged here rather than silently skipped —
worth a small follow-up before this ships.

## What step 6 deliberately does not do

- No widget resizing (wide/narrow) — order + visibility is the
  customization surface. Sizing would need a real grid-layout model
  (columns/rows) this step didn't scope; noted as a natural follow-up, not
  built as a half-finished stub.
- No cross-device sync conflict handling beyond last-write-wins (the
  service layer's `set` always replaces the single row) — acceptable for
  a personal preference, same as any other per-user setting in this app.

## Open items carried forward

- **Step 7 remains split, per the kickoff doc's own sequencing**: Tier 2
  config toggles are still blocked on Sepiso Toni's sign-off on Decision 2
  (the A/B comparison doc shipped in the kickoff package is proposal-only
  — nothing implemented, as instructed). Tier 3 plugin-owned pages
  (`app/marketplace/[pluginId]`) don't depend on Decision 2 and could
  start independently — not yet built.
- The ESLint flat-config gap noted above.
