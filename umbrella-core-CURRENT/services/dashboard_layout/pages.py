"""
services/dashboard_layout/pages.py — the explicit allow-list of which
dashboard pages support a custom per-user layout (Phase 10 step 6).

PHASE10-BUILD-KICKOFF-HANDOFF.md item 6 is specific: "Explicitly enumerate
which pages are customizable — not 'all of them' — and design a real
default widget arrangement per customizable page, not a placeholder."

Today that's exactly one page. Walking the actual route set
(`umbrella-dashboard/lib/nav-config.ts` as of step 5):

- `/dashboard`  — fed by the `dashboard.widgets` Tier 1 slot
  (`marketplace.install.dashboard_slots`). Real, per-installation, plugin
  -contributed widget set. This is the one page a "layout" means anything
  concrete for.
- `/marketplace` — a plugin listing/install table. Not widget-fed; there
  is nothing to reorder.
- `/topology` — a two-layer canvas (step 5). The "layout" is the toggle
  between the infra layer and the dependency layer, which is already
  client-side view state, not a persisted arrangement of discrete cards.
  Force-fitting it into this model would mean inventing a widget concept
  that doesn't exist for this page.

So `CUSTOMIZABLE_PAGES` has one entry. This is deliberately a registry,
not a hardcoded `Literal["dashboard"]` scattered across the capability and
route layers, so a future customizable page (a Tier 3 plugin page wanting
its own layout, once step 7 builds `app/marketplace/[pluginId]`) is one
line here, not a signature change everywhere `page_id` is validated.

`default_widget_source` documents where "no saved layout yet" falls back
to for that page — for `dashboard` that's simply whatever order
`marketplace.install.dashboard_slots` returns today (registration order),
which is also exactly what step 3 already rendered before this step
existed. Step 6 does not change that default; it only adds the ability to
override it per user.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CustomizablePage:
    page_id: str
    label: str
    # Human-readable note on what "default arrangement" means for this
    # page today — not machine-consumed, just keeps the reasoning next to
    # the registry entry instead of only in this module's docstring.
    default_widget_source: str


CUSTOMIZABLE_PAGES: dict[str, CustomizablePage] = {
    "dashboard": CustomizablePage(
        page_id="dashboard",
        label="Dashboard",
        default_widget_source=(
            "marketplace.install.dashboard_slots(slot='dashboard.widgets') in the order "
            "that capability returns them — i.e. plugin registration order. No layout row "
            "means 'use that order, all widgets visible'."
        ),
    ),
}


def is_customizable(page_id: str) -> bool:
    return page_id in CUSTOMIZABLE_PAGES
