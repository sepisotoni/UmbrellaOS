import { getSession } from "@/lib/session";
import { fetchPageLayout, resolvePageWidgets } from "@/lib/marketplace-pages";
import { PluginWidget } from "@/components/widgets/plugin-widget";

// Phase 10, Tier 3, Decision 5: ONE generic dynamic route for every
// plugin's page — not one hand-written .tsx per plugin. This fetches the
// plugin's declared layout server-side and renders it through the same
// trusted widget dispatcher Tier 1 uses (Decision 1), now including
// "table" (lib/widgets & components/widgets/plugin-widget.tsx).
//
// Strictly opt-in, enforced end-to-end: marketplace.install.page_layout
// 404s for a plugin that isn't installed or never declared a page
// (services/plugins/marketplace_service.py::page_layout), and
// fetchPageLayout turns that into `null` here — this route renders a
// plain "nothing here" message for that case, not a broken page or a
// silently-empty grid that looks like a loading bug.
export default async function PluginPage({
  params,
}: {
  params: Promise<{ pluginId: string }>;
}) {
  const { pluginId } = await params;
  const session = await getSession();
  if (!session) {
    return <p className="text-sm opacity-60">Sign in to view this page.</p>;
  }

  const layout = await fetchPageLayout(pluginId, session.token);
  if (!layout) {
    return (
      <p className="text-sm opacity-60">
        &quot;{pluginId}&quot; isn&apos;t installed, or doesn&apos;t declare a dashboard page.
      </p>
    );
  }

  const widgets = await resolvePageWidgets(layout, session.token);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">{layout.nav_label}</h1>
      {widgets.length === 0 ? (
        <p className="text-sm opacity-60">
          No widget data is currently available for this page.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {widgets.map(({ decl, data }) => (
            <PluginWidget key={decl.capability_name} decl={decl} data={data} />
          ))}
        </div>
      )}
    </div>
  );
}
