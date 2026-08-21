import { getSession } from "@/lib/session";
import { resolveSlotWidgets } from "@/lib/widgets";
import { fetchLayout, applyLayout, widgetKey } from "@/lib/dashboard-layout";
import { PluginWidget } from "./plugin-widget";
import { DashboardCustomizer } from "./dashboard-customizer";

// Phase 10 step 6: this is now a two-part render. The grid itself stays a
// server component (Decision 6) — layout resolution is a data concern, not
// an interaction, so it doesn't need to run in the browser. Only the
// "customize" affordance (DashboardCustomizer) is a client leaf, and it
// receives the already-resolved widget list as plain serializable props
// (key + label + visible), never plugin data itself — same
// no-plugin-data-reaches-untrusted-code boundary Decision 1 already holds
// for rendering, extended to the ordering UI.
export async function WidgetGrid() {
  const session = await getSession();
  if (!session) return null;

  const [liveWidgets, savedLayout] = await Promise.all([
    resolveSlotWidgets("dashboard.widgets", session.token),
    fetchLayout("dashboard", session.token),
  ]);

  const orderedWidgets = applyLayout(liveWidgets, savedLayout);

  const customizerEntries = liveWidgets.map((w) => {
    const key = widgetKey(w);
    const saved = savedLayout?.find((s) => s.widget_key === key);
    return { widgetKey: key, label: w.decl.label, visible: saved ? saved.visible : true };
  });
  // Customizer's own list follows the resolved (saved-order-first) arrangement
  // too, so "what you see is what you're reordering."
  const orderedKeys = orderedWidgets.map(widgetKey);
  customizerEntries.sort((a, b) => {
    const ai = orderedKeys.indexOf(a.widgetKey);
    const bi = orderedKeys.indexOf(b.widgetKey);
    return ai - bi;
  });

  if (liveWidgets.length === 0) {
    return <p className="text-sm opacity-60">No dashboard widgets installed yet.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <DashboardCustomizer pageId="dashboard" initialWidgets={customizerEntries} />
      </div>
      {orderedWidgets.length === 0 ? (
        <p className="text-sm opacity-60">
          All widgets are hidden.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {orderedWidgets.map((w) => (
            <PluginWidget key={widgetKey(w)} decl={w.decl} data={w.data} />
          ))}
        </div>
      )}
    </div>
  );
}
