// app/(dashboard)/marketplace/page.tsx — Task A (Phase 10 completion):
// the marketplace catalog/install UI, replacing the step-2 placeholder.
// Route name reserved per Decision 4 (see the placeholder comment this
// replaced) — "marketplace", not "plugins" (already taken by the
// unrelated Bukkit/Paper Plugin concept).
//
// Explicitly NOT in scope (confirmed against SUBCHAT-HANDOFF-PHASE10-
// COMPLETION.md before building): marketplace.listing.publish (a plugin
// author uploading a new zip) — that's a separate, larger UI (file
// upload, zip validation feedback), not part of "Phase 10 is done."
import { redirect } from "next/navigation";
import Link from "next/link";
import { getSession, hasPermission } from "@/lib/session";
import { fetchInstalledPlugins, fetchMarketplaceListings } from "@/lib/marketplace-listings";
import { MarketplaceInstallButton } from "@/components/widgets/marketplace-install-button";

export default async function MarketplacePage() {
  const session = await getSession();
  if (!session) redirect("/login");

  // Both list fetches run independently and each degrade to an empty
  // array on failure (see lib/marketplace-listings.ts) — a listing-read
  // failure shouldn't hide plugins the user already has installed, and
  // vice versa.
  const [listings, installed] = await Promise.all([
    fetchMarketplaceListings(session.token),
    fetchInstalledPlugins(session.token),
  ]);

  const installedByPluginId = new Map(installed.map((i) => [i.plugin_id, i]));
  const canManage = hasPermission(session.user, "marketplace.install.manage");

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Marketplace</h1>
      {listings.length === 0 ? (
        <p className="text-sm opacity-60">
          No plugins are currently published to the marketplace catalog.
        </p>
      ) : (
        <div className="space-y-2">
          {listings.map((listing) => {
            const install = installedByPluginId.get(listing.plugin_id);
            return (
              <section
                key={listing.plugin_id}
                className="flex items-start justify-between gap-4 rounded-lg border border-[var(--border)] p-4"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/marketplace/${encodeURIComponent(listing.plugin_id)}`}
                      className="text-sm font-medium hover:underline"
                    >
                      {listing.name}
                    </Link>
                    {install && (
                      <span className="rounded bg-[var(--accent)]/20 px-1.5 py-0.5 text-xs text-[var(--accent)]">
                        Installed v{install.installed_version}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs opacity-60">
                    {listing.description || "No description provided."}
                  </p>
                  <p className="mt-1 text-xs opacity-40">
                    by {listing.author} · latest v{listing.latest_version}
                  </p>
                </div>
                <MarketplaceInstallButton
                  pluginId={listing.plugin_id}
                  latestVersion={listing.latest_version}
                  installedVersion={install?.installed_version ?? null}
                  canManage={canManage}
                />
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
