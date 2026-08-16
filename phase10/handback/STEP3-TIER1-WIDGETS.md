# Step 3 — Tier 1 widgets: manifest & handback

Built directly against step 0's live-verified shapes, not the scoping
doc's assumptions — `capability_name`, `plugin_id`, `render_as` all
consumed as confirmed in `handback/STEP0-MARKETPLACE-SHAPE-VERIFICATION.md`.

## New files

```
lib/widgets.ts          — fetchSlots / fetchWidgetData / resolveSlotWidgets
lib/widget-shape.ts      — inferRenderAs fallback (Decision 7)
components/widgets/stat-pair.tsx
components/widgets/status-badge.tsx
components/widgets/simple-list.tsx
components/widgets/plugin-widget.tsx   — dispatches render_as -> trusted component
components/widgets/widget-grid.tsx     — dashboard.widgets, used on the dashboard page
components/widgets/sidebar-widgets.tsx — sidebar.tools / sidebar.moderation, used in Sidebar
```

Changed: `app/(dashboard)/dashboard/page.tsx` (renders `WidgetGrid`),
`components/nav/sidebar.tsx` (now async, renders `SidebarWidgets` for both
sidebar slots), `app/(dashboard)/layout.tsx` (passes `session.token`
through to `Sidebar`).

## Rendering model — Decision 1, held exactly

Three trusted components (`stat-pair.tsx`, `status-badge.tsx`,
`simple-list.tsx`) do 100% of the rendering. A plugin's capability result
is plain JSON that flows into `{value}`/`{String(value)}` JSX
interpolation — never `dangerouslySetInnerHTML`, never eval'd, never
templated into a string that gets parsed as markup. `plugin-widget.tsx` is
the only file that reads `decl.render_as`, and it only uses it to pick
*which* trusted component runs — the plugin never supplies the component
itself. This holds for all three declared slots (`dashboard.widgets`,
`sidebar.tools`, `sidebar.moderation`), since the manifest schema uses the
identical `render_as` vocabulary for all three (confirmed in
`services/plugins/manifest.py`, `_DASHBOARD_SLOTS` /
`_ALLOWED_RENDER_AS`) — not just the one slot the scoping doc's Tier 1
section named in its heading.

## Decision 7 (inference fallback) — implemented as graceful degradation

`lib/widget-shape.ts::inferRenderAs` runs only when `decl.render_as` is
`null`, and follows the scoping doc's rule exactly: array → `simple_list`;
single-key object with a string `status` field → `status_badge`;
otherwise → `stat_pair`. `render_as` is checked first every time
(`plugin-widget.tsx`: `decl.render_as ?? inferRenderAs(data)`).

## A gap the step 0 verification surfaced, handled here

`DashboardSlotResult` (and therefore `marketplace.install.dashboard_slots`)
does not expose the underlying capability's `required_permission` — a
staff user can see that a slot exists without necessarily holding
permission to invoke it. `lib/widgets.ts::fetchWidgetData` catches each
widget's data fetch independently and returns `null` on any failure (403,
plugin sandbox error, anything) rather than letting one widget's failure
take down the whole grid or sidebar section — `resolveSlotWidgets` filters
those out before anything reaches a trusted component. Not spelled out in
either the kickoff doc or the scoping doc; flagging it here since it's a
real behavior decision, not an obvious default.

## What is NOT independently verified, same caveat as step 2

Still no network access in this sandbox — `npm ci` / `npm run build` /
`npm run lint` have not been run against these additions either. The
render components are simple enough (plain JSX, no new dependencies) that
the risk surface is smaller than step 2's OAuth/cookie plumbing, but the
same three commands from `STEP2-DASHBOARD-SCAFFOLD.md` need to run in an
environment with registry access before this step gets the "independently
re-verified" stamp the kickoff doc asks for on every step.
