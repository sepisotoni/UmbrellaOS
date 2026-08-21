import { StatPair } from "./stat-pair";
import { StatusBadge } from "./status-badge";
import { SimpleList } from "./simple-list";
import { TableWidget } from "./table-widget";
import { inferRenderAs } from "@/lib/widget-shape";
import type { WidgetData } from "@/lib/widgets";
import type { RenderAs } from "@/lib/types";

// The only place a slot's or page widget's declared render_as gets
// consulted. render_as is the reliable path; inference is graceful
// degradation for plugins that don't declare it (Decision 7) — never the
// other way around.
//
// `decl` is intentionally the minimal structural shape both Tier 1's
// DashboardSlot and Tier 3's PageWidget satisfy (label + render_as) rather
// than importing DashboardSlot by name — this dispatcher is genuinely
// tier-agnostic (Decision 1: one trusted rendering model for every tier),
// so it shouldn't need a parallel copy for Tier 3's dynamic route to reuse
// it. "table" is reachable here for real now that Tier 3 exists; it
// remains unreachable in practice for a Tier 1 slot since the manifest
// schema itself rejects render_as="table" on dashboard_ui_slots.
type WidgetDecl = { label: string; render_as: RenderAs };

export function PluginWidget({ decl, data }: { decl: WidgetDecl; data: WidgetData }) {
  const shape = decl.render_as ?? inferRenderAs(data);

  switch (shape) {
    case "status_badge":
      return <StatusBadge label={decl.label} data={data as Record<string, unknown>} />;
    case "simple_list":
      return <SimpleList label={decl.label} data={data as unknown[]} />;
    case "table":
      return <TableWidget label={decl.label} data={data as unknown[]} />;
    case "stat_pair":
    default:
      return <StatPair label={decl.label} data={data as Record<string, unknown>} />;
  }
}
