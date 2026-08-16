import { resolveSlotWidgets } from "@/lib/widgets";
import { PluginWidget } from "./plugin-widget";
import type { DashboardSlotName } from "@/lib/types";

// Same trusted rendering path as the dashboard grid — the sidebar just
// stacks the cards in one column instead of a grid. sidebar.tools and
// sidebar.moderation are separate slot values (a plugin picks one, not
// both), so this renders one at a time; the sidebar itself calls it twice.
export async function SidebarWidgets({
  slot,
  token,
}: {
  slot: DashboardSlotName;
  token: string;
}) {
  const widgets = await resolveSlotWidgets(slot, token);
  if (widgets.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 border-t border-[var(--border)] p-4">
      {widgets.map(({ decl, data }) => (
        <PluginWidget key={`${decl.plugin_id}:${decl.capability_name}`} decl={decl} data={data} />
      ))}
    </div>
  );
}
