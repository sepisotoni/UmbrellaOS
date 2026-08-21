// lib/plugin-sandbox.ts — server-only data fetching for Phase 8
// completion's plugin debugger (Task B), profiler (Task C), and sandbox
// visualizer (Task D). Backed entirely by capabilities/plugin_sandbox.py's
// four new capabilities — no new backend plumbing beyond what that
// dispatch's Task A/B.1/C.1/D already built; this file is UI-side only,
// same shape as lib/fleet.ts and lib/activity.ts.
import "server-only";
import { invokeCapability } from "./api";
import type {
  PluginExecutionDetail,
  PluginExecutionHistoryResult,
  PluginExecutionProfile,
  PluginSandboxLimits,
} from "./types";

export async function fetchExecutionHistory(
  token: string,
  params: { limit: number; offset: number; pluginId?: string; outcome?: string }
): Promise<PluginExecutionHistoryResult> {
  try {
    return await invokeCapability<PluginExecutionHistoryResult>(
      "plugin.sandbox.execution_history",
      {
        limit: params.limit,
        offset: params.offset,
        plugin_id: params.pluginId || undefined,
        outcome: params.outcome || undefined,
      },
      token
    );
  } catch {
    return { entries: [], total: 0, limit: params.limit, offset: params.offset };
  }
}

/** Null means "not found or not permitted" — the debugger page treats
 * that as a 404-shaped inline message rather than distinguishing the two,
 * matching every other capability-backed page in this app (fetchServerStats,
 * fetchAuditLog): a capability-call failure here is never surfaced as a
 * raw error, just "nothing to show." */
export async function fetchExecutionDetail(
  executionId: string,
  token: string
): Promise<PluginExecutionDetail | null> {
  try {
    return await invokeCapability<PluginExecutionDetail>(
      "plugin.sandbox.execution_detail",
      { execution_id: executionId },
      token
    );
  } catch {
    return null;
  }
}

export async function fetchProfile(
  token: string,
  params: { windowHours?: number; pluginId?: string } = {}
): Promise<PluginExecutionProfile[]> {
  try {
    return await invokeCapability<PluginExecutionProfile[]>(
      "plugin.sandbox.profile",
      { window_hours: params.windowHours ?? 24, plugin_id: params.pluginId || undefined },
      token
    );
  } catch {
    return [];
  }
}

export async function fetchSandboxLimits(token: string): Promise<PluginSandboxLimits | null> {
  try {
    return await invokeCapability<PluginSandboxLimits>("plugin.sandbox.limits", {}, token);
  } catch {
    return null;
  }
}
