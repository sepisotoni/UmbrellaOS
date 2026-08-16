// lib/marketplace-listings.ts — server-only Task A (Phase 10 completion)
// data fetching: the marketplace catalog + what's currently installed.
// Deliberately separate from lib/marketplace-pages.ts even though the
// module name is close — that file is Tier 3 (an installed plugin's own
// declared page), this one is the marketplace browse/install surface
// itself (Decision 4's original, still-open "not yet built" item). Same
// catch-and-degrade-to-empty-array posture every other list fetch in this
// app already uses (fetchPluginNavEntries, fetchConfigurablePlugins) — a
// 403 (caller lacks marketplace.listing.view / marketplace.install.view)
// or any other read failure degrades to an empty catalog/install list,
// not a broken page.
import "server-only";
import { invokeCapability } from "./api";
import type { PluginInstall, PluginListing, PluginVersion } from "./types";

// ---------------------------------------------------------------------
// Writes (install/uninstall). Left to throw on failure, same as
// lib/plugin-config.ts::setPluginConfigValue — app/api/marketplace-install/
// route.ts is the layer that needs to distinguish "succeeded" from
// "failed" (and, per capabilities/marketplace.py, from "not found" /
// "already installed at that version") to answer the client correctly,
// so this is not the layer that should swallow the error.
// ---------------------------------------------------------------------

export async function fetchMarketplaceListings(token: string): Promise<PluginListing[]> {
  try {
    return await invokeCapability<PluginListing[]>("marketplace.listing.list", {}, token);
  } catch {
    return [];
  }
}

export async function fetchInstalledPlugins(token: string): Promise<PluginInstall[]> {
  try {
    return await invokeCapability<PluginInstall[]>("marketplace.install.list", {}, token);
  } catch {
    return [];
  }
}

/** Every published version of one plugin, oldest first (mirrors
 * MarketplaceService.list_versions's own ordering — see
 * capabilities/marketplace.py). Same catch-and-degrade posture as the two
 * list fetches above: a 403/404/network failure degrades to an empty
 * version list rather than throwing, since this only ever backs an
 * install/update version picker, never a page's core content. */
export async function fetchPluginVersions(pluginId: string, token: string): Promise<PluginVersion[]> {
  try {
    return await invokeCapability<PluginVersion[]>(
      "marketplace.listing.versions",
      { plugin_id: pluginId },
      token
    );
  } catch {
    return [];
  }
}

/** Installs (or updates, if a different version is already installed —
 * see MarketplaceService.install's own docstring) a plugin version.
 * `marketplace.install.install` is `destructive: true` server-side (real
 * manifest validation + sandbox setup, not instant — install runs longer
 * than a config toggle), so callers of this should show a pending state
 * rather than assuming it resolves immediately. */
export async function installPlugin(
  pluginId: string,
  version: string,
  token: string
): Promise<PluginInstall> {
  return invokeCapability<PluginInstall>(
    "marketplace.install.install",
    { plugin_id: pluginId, version },
    token
  );
}

export async function uninstallPlugin(pluginId: string, token: string): Promise<void> {
  await invokeCapability<{ uninstalled: boolean }>(
    "marketplace.install.uninstall",
    { plugin_id: pluginId },
    token
  );
}
