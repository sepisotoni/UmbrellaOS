// lib/dashboard-layout.ts — server-only helpers for Phase 10 step 6.
//
// Two responsibilities, deliberately kept in one small file rather than
// split like lib/widgets.ts/lib/api.ts: (1) call the three
// dashboard.layout.* capabilities, and (2) merge a saved layout with the
// *live* widget set a page actually has right now.
//
// The merge in `applyLayout` is the part worth documenting: a saved layout
// only ever stores what a user explicitly customized, never a full
// snapshot (see umbrella-core's models/dashboard_layout.py docstring for
// why) — so a widget_key with no entry in the saved layout is NOT the same
// as "hidden." It means "not customized yet," which resolves to
// "visible, appended after the customized ones, in the page's own default
// order" — otherwise installing a new plugin after saving a layout would
// silently hide its widget forever, which is worse than the layout feature
// not existing.
import "server-only";
import { invokeCapability } from "./api";
import type { DashboardLayoutResult, LayoutWidgetEntry } from "./types";
import type { ResolvedWidget } from "./widgets";

export async function fetchLayout(
  pageId: string,
  token: string
): Promise<LayoutWidgetEntry[] | null> {
  try {
    const result = await invokeCapability<DashboardLayoutResult>(
      "dashboard.layout.get",
      { page_id: pageId },
      token
    );
    return result.widgets;
  } catch {
    // Same independent-failure posture as every other Tier 1 fetch in this
    // app (lib/widgets.ts) — a layout-fetch failure degrades to "use the
    // default arrangement," it never breaks the page.
    return null;
  }
}

export async function saveLayout(
  pageId: string,
  widgets: LayoutWidgetEntry[],
  token: string
): Promise<void> {
  await invokeCapability("dashboard.layout.set", { page_id: pageId, widgets }, token);
}

export async function resetLayout(pageId: string, token: string): Promise<void> {
  await invokeCapability("dashboard.layout.reset", { page_id: pageId }, token);
}

export function widgetKey(widget: ResolvedWidget): string {
  return `${widget.decl.plugin_id}:${widget.decl.capability_name}`;
}

/**
 * Reorders/filters the page's live widgets by a saved layout.
 *
 * - Widgets with a saved entry: kept in the saved order, visible per the
 *   saved `visible` flag.
 * - Widgets with no saved entry (newly installed since the layout was last
 *   saved, or `savedWidgets` is null because nothing's been customized
 *   yet): appended after the customized ones, in the page's own default
 *   (live) order, always visible.
 * - A saved entry whose widget_key no longer matches any live widget
 *   (the plugin was uninstalled) is simply dropped — nothing to render.
 */
export function applyLayout(
  liveWidgets: ResolvedWidget[],
  savedWidgets: LayoutWidgetEntry[] | null
): ResolvedWidget[] {
  if (savedWidgets === null || savedWidgets.length === 0) return liveWidgets;

  const liveByKey = new Map(liveWidgets.map((w) => [widgetKey(w), w]));
  const seen = new Set<string>();
  const ordered: ResolvedWidget[] = [];

  for (const entry of savedWidgets) {
    const widget = liveByKey.get(entry.widget_key);
    if (!widget) continue; // uninstalled since the layout was saved
    seen.add(entry.widget_key);
    if (entry.visible) ordered.push(widget);
  }

  for (const widget of liveWidgets) {
    if (!seen.has(widgetKey(widget))) ordered.push(widget);
  }

  return ordered;
}
