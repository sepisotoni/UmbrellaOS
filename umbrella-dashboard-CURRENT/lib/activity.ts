// lib/activity.ts — server-only data fetching for the activity timeline
// (Phase 10 closeout, Task 1). Backed entirely by the existing
// `platform.audit.search` capability (capabilities/system.py) — no new
// backend plumbing, per the dispatch's "this is a UI-only dispatch"
// instruction.
//
// Same catch-and-degrade-to-empty posture as every other list fetch in
// this app (fetchMarketplaceListings, fetchConfigurablePlugins): a 403
// (caller lacks `audit.view`) or any other read failure degrades to an
// empty page rather than a broken one. In practice the page itself
// already checks `audit.view` via `hasPermission` before calling this
// (see app/(dashboard)/activity/page.tsx), matching
// lib/topology.ts::buildAvailableLayers's "check permission before
// fetching" pattern — this degrade is the second line of defense, not
// the only one.
import "server-only";
import { invokeCapability } from "./api";
import type { AuditSearchResult } from "./types";

export type AuditSearchFilters = {
  limit?: number;
  offset?: number;
  actorType?: string;
  action?: string;
};

export async function fetchAuditLog(
  token: string,
  filters: AuditSearchFilters = {}
): Promise<AuditSearchResult> {
  const limit = filters.limit ?? 25;
  const offset = filters.offset ?? 0;
  try {
    return await invokeCapability<AuditSearchResult>(
      "platform.audit.search",
      {
        limit,
        offset,
        actor_type: filters.actorType ?? null,
        action: filters.action ?? null,
      },
      token
    );
  } catch {
    return { entries: [], total: 0, limit, offset };
  }
}
