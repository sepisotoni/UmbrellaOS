// lib/widget-shape.ts — shape-based inference fallback for a slot that
// didn't declare render_as (Decision 7: "render_as is the reliable path,
// inference is graceful degradation, not the other way around" —
// DASHBOARD-PLUGIN-UI-SCOPING.md). Mirrors the exact rule from that doc:
// array → list; object with a lone `status` string → badge; otherwise
// every top-level scalar → stat-pair.
import type { WidgetData } from "./widgets";

export type InferredRenderAs = "stat_pair" | "status_badge" | "simple_list";

export function inferRenderAs(data: WidgetData): InferredRenderAs {
  if (Array.isArray(data)) return "simple_list";
  const keys = Object.keys(data);
  if (keys.length === 1 && typeof data.status === "string") {
    return "status_badge";
  }
  return "stat_pair";
}
