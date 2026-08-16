# Step 5 — Topology map: manifest & handback

## Roadmap decision held exactly

`UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md`, locked answer #1: infra
(Phase 2's node/server topology) and capability dependencies (Phase 8's
plugin/capability graph) as **two toggleable layers over one canvas, not
one mixed graph**. `components/topology/topology-canvas.tsx` renders
exactly one layer at a time from a shared `TopologyLayer` shape
(`lib/topology-types.ts`) — nodes and edges are drawn identically
regardless of which layer is active; only the data differs.

## New files

```
lib/topology-types.ts    — shared TopologyNode/TopologyEdge/TopologyLayer shape
lib/topology.ts           — server-only layer builders + permission-gated buildAvailableLayers
components/topology/topology-canvas.tsx  — the one client leaf: layer toggle + SVG render
app/(dashboard)/topology/page.tsx        — fetches both layers server-side, hands to the canvas
```

Changed: `lib/nav-config.ts` (added `/topology`, unlocked by either
`hosting.node.view` or `marketplace.install.view` — `visibleNavItems`
already OR-matches a nav item's permission list, so a user with only one
of the two still sees the link), `middleware.ts` (added `/topology` to
the protected-route prefixes/matcher).

## What the "capability dependency" layer actually renders, and why

There is no "capability A calls capability B" edge anywhere in this
codebase — checked `registry/spec.py` and `registry/registry.py`
directly, nothing tracks inter-capability calls. What **is** real and
queryable is the plugin-registers-capability relationship: each installed
plugin's `registered_capability_names` (from `marketplace.install.list`,
the same field steps 0 and 3 already consume). That's what "Phase 8's
plugin/capability graph" in the roadmap doc's own wording refers to, and
it's what this layer draws — plugin nodes on the left, the capabilities
each one registered on the right, one edge per registration. Not a
speculative richer graph the backend doesn't actually have data for.

## Layout choice — no new dependency added

Both layers happen to be a two-tier bipartite graph today (host → server;
plugin → capability), so `topology-canvas.tsx` uses one simple two-column
layout function rather than pulling in a force-directed graph library
(`d3-force`, `dagre`, etc.). That's a deliberate scope decision, not an
oversight: this sandbox still has no network access to verify a new
dependency actually installs (same constraint as every prior step), and
the two real datasets available today don't need anything fancier to be
legible. If a future layer's shape stops being a clean two-tier
hierarchy, this is the file to revisit — noted in its own header comment
so it isn't missed.

## Permission handling

`buildAvailableLayers` only fetches a layer if the caller holds every
permission that layer's underlying capabilities require (`hosting.node.view`
+ `hosting.server.view` for infra; `marketplace.install.view` for
dependencies), and catches a fetch failure per layer independently — same
"don't let one thing fail the whole page" posture as steps 3 and 4. A
user with only one of the two permission sets sees one layer with no
toggle control at all (the toggle only renders when `available.length > 1`
in `topology-canvas.tsx`), not a disabled tab pointing at data they can't
see.

## What is NOT independently verified, same caveat as steps 2-4

Still no network access in this sandbox. This step's SVG rendering has no
new npm dependencies (plain `<svg>`/`<line>`/`<rect>`/`<text>`, no chart
library), which narrows the risk surface versus step 4's client
interactivity, but `npm run build` + a visual check of the layout math
(row spacing, edge endpoints) still need to happen in an environment with
registry access before this is trusted as done.
