// lib/marketplace-pages.ts — server-only Tier 3 (plugin-owned pages) data
// fetching. Deliberately separate from lib/widgets.ts even though the
// shapes overlap: this layer's failure semantics differ — a missing/
// unauthorized nav list degrades to "no plugin pages in the sidebar"
// (same posture as lib/widgets.ts's fetchSlots), but a direct visit to
// /marketplace/[pluginId] for a plugin with no page needs to distinguish
// "nothing here" from a real error, not just silently render nothing.
import "server-only";
import { ApiError, invokeCapability } from "./api";
import { fetchWidgetData, type WidgetData } from "./widgets";
import type { PageLayout, PageNav, PageWidget } from "./types";

/** Nav metadata for every installed plugin that declared a page — what
 * the sidebar needs to build its plugin-page links. Same
 * catch-and-degrade posture as lib/widgets.ts::fetchSlots: a 403 (caller
 * lacks marketplace.install.view) or any other failure just means no
 * plugin-page links show up, not a broken sidebar. */
export async function fetchPluginNavEntries(token: string): Promise<PageNav[]> {
  try {
    return await invokeCapability<PageNav[]>("marketplace.install.pages", {}, token);
  } catch {
    return [];
  }
}

/** The declared layout for one plugin's page, or null if the plugin isn't
 * installed or never declared a page (marketplace.install.page_layout
 * returns 404 for both — see services/plugins/marketplace_service.py's
 * page_layout() docstring). null here is the signal the route uses to
 * render a "nothing here" message instead of the page grid — distinct
 * from a genuine backend outage, which is left to throw and hit the
 * route's error boundary rather than being silently swallowed into the
 * same "nothing here" message. */
export async function fetchPageLayout(pluginId: string, token: string): Promise<PageLayout | null> {
  try {
    return await invokeCapability<PageLayout>(
      "marketplace.install.page_layout",
      { plugin_id: pluginId },
      token
    );
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 403)) {
      return null;
    }
    throw err;
  }
}

export type ResolvedPageWidget = { decl: PageWidget; data: WidgetData };

/** Resolves each declared widget's live data independently — same
 * per-widget failure isolation as lib/widgets.ts::resolveSlotWidgets
 * (one plugin capability erroring or 403ing skips that one card, never
 * the whole page). */
export async function resolvePageWidgets(layout: PageLayout, token: string): Promise<ResolvedPageWidget[]> {
  const resolved = await Promise.all(
    layout.widgets.map(async (decl) => ({
      decl,
      data: await fetchWidgetData(decl.capability_name, token),
    }))
  );
  return resolved.filter((w): w is ResolvedPageWidget => w.data !== null);
}
