// lib/widgets.ts — server-only Tier 1 data-fetching helpers, shared by the
// dashboard grid and the sidebar. Kept separate from lib/api.ts because
// this layer knows about the per-widget failure semantics; lib/api.ts
// stays a generic client.
import "server-only";
import { invokeCapability } from "./api";
import type { DashboardSlot, DashboardSlotName } from "./types";

export type WidgetData = Record<string, unknown> | unknown[];

export async function fetchSlots(
  slot: DashboardSlotName,
  token: string
): Promise<DashboardSlot[]> {
  try {
    return await invokeCapability<DashboardSlot[]>(
      "marketplace.install.dashboard_slots",
      { slot },
      token
    );
  } catch {
    return [];
  }
}

/** A slot being listable does NOT mean the caller holds the underlying
 * capability's required_permission — DashboardSlotResult doesn't expose
 * that field at all (see handback/STEP0-MARKETPLACE-SHAPE-VERIFICATION.md).
 * So every widget's data fetch is caught independently: one plugin's 403,
 * or a sandboxed plugin runtime error, skips that one card, never the
 * whole slot. */
export async function fetchWidgetData(
  capabilityName: string,
  token: string
): Promise<WidgetData | null> {
  try {
    const data = await invokeCapability<WidgetData>(capabilityName, {}, token);
    return data;
  } catch {
    return null;
  }
}

export type ResolvedWidget = { decl: DashboardSlot; data: WidgetData };

export async function resolveSlotWidgets(
  slot: DashboardSlotName,
  token: string
): Promise<ResolvedWidget[]> {
  const decls = await fetchSlots(slot, token);
  const resolved = await Promise.all(
    decls.map(async (decl) => ({ decl, data: await fetchWidgetData(decl.capability_name, token) }))
  );
  return resolved.filter((w): w is ResolvedWidget => w.data !== null);
}
