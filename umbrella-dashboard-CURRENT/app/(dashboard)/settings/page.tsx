// app/(dashboard)/settings/page.tsx — Phase 10 step 8's frontend half:
// renders every installed plugin's Tier 2 dashboard-configurable fields.
// Per STEP8-TIER2-CONFIG-TOGGLES-BACKEND.md's handback: this is the one
// concrete remaining build item from that package. Not the right home for
// Tier 3 plugin pages (those are /marketplace/[pluginId], already
// distinct) — this route is strictly the boolean-toggle Settings surface
// Decision 2 (Option A) scoped.
import { redirect } from "next/navigation";
import { getSession, hasPermission } from "@/lib/session";
import { fetchConfigurablePlugins, fetchPluginConfigValues } from "@/lib/plugin-config";
import { PluginConfigToggle } from "@/components/widgets/plugin-config-toggle";

export default async function SettingsPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const plugins = await fetchConfigurablePlugins(session.token);

  // Per-plugin values fetched independently (same isolation as
  // resolvePageWidgets) — one plugin's config.get failing degrades that
  // one card to "no settings loaded," never the whole page. canWrite is
  // computed here (not in the toggle itself) because it's a per-plugin
  // permission (`plugin.<id>.config.write`, auto-registered alongside
  // .get/.set in services/plugins/registration.py) — the backend already
  // enforces this on every write, this is purely a UX signal so a
  // read-only user (marketplace.install.view without this plugin's own
  // config.write grant) sees a disabled toggle instead of an optimistic
  // flip that reverts with a generic error.
  const withValues = await Promise.all(
    plugins.map(async (plugin) => ({
      plugin,
      values: await fetchPluginConfigValues(plugin.plugin_id, session.token),
      canWrite: hasPermission(session.user, `plugin.${plugin.plugin_id}.config.write`),
    }))
  );

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card/80 px-5 py-5"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">UmbrellaOS / Configuration</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Settings</h1><p className="mt-2 text-sm leading-6 text-muted-foreground">Tune installed extensions without leaving the control room.</p></div>
      {withValues.length === 0 ? (
        <p className="text-sm opacity-60">
          No installed plugins have dashboard-configurable settings yet.
        </p>
      ) : (
        <div className="space-y-4">
          {withValues.map(({ plugin, values, canWrite }) => (
            <section
              key={plugin.plugin_id}
              className="rounded-lg border border-[var(--border)] p-4"
            >
              <h2 className="mb-2 text-sm font-medium">{plugin.plugin_name}</h2>
              {values.length === 0 ? (
                <p className="text-xs opacity-60">Settings unavailable right now.</p>
              ) : (
                <div className="space-y-1">
                  {values.map((field) => (
                    <PluginConfigToggle
                      key={field.key}
                      pluginId={plugin.plugin_id}
                      fieldKey={field.key}
                      label={field.label}
                      initialValue={field.value}
                      canWrite={canWrite}
                    />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
