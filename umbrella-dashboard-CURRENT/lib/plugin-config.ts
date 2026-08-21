// lib/plugin-config.ts — server-only Tier 2 (dashboard-configurable plugin
// settings) data fetching, following lib/marketplace-pages.ts's exact
// pattern for the Tier 3 page equivalent: list nav-weight metadata once
// (fetchConfigurablePlugins), then fetch each plugin's live values
// per-item (fetchPluginConfigValues). The write path is a separate call
// (setPluginConfigValue) — this file never mutates state itself, that's
// app/api/plugin-config/route.ts's job, same split as lib/dashboard-layout.ts
// vs its route.

import "server-only";
import { invokeCapability } from "./api";
import type { ConfigFieldValue, ConfigGetResult, ConfigurablePlugin } from "./types";

/** Every installed plugin that declared at least one Tier 2 config field.
 * Same catch-and-degrade posture as fetchPluginNavEntries: a 403
 * (caller lacks marketplace.install.view) or any other failure just means
 * the Settings page renders as empty, not broken. */
export async function fetchConfigurablePlugins(token: string): Promise<ConfigurablePlugin[]> {
  try {
    return await invokeCapability<ConfigurablePlugin[]>(
      "marketplace.install.configurable_plugins",
      {},
      token
    );
  } catch {
    return [];
  }
}

/** One plugin's current config field values, via its auto-registered
 * `plugin.<plugin_id>.config.get` capability (services/plugins/registration.py).
 * Degrades to an empty list on failure rather than throwing — one plugin's
 * config being unreadable shouldn't take down the whole Settings page,
 * same per-item isolation as resolvePageWidgets. */
export async function fetchPluginConfigValues(
  pluginId: string,
  token: string
): Promise<ConfigFieldValue[]> {
  try {
    const result = await invokeCapability<ConfigGetResult>(
      `plugin.${pluginId}.config.get`,
      {},
      token
    );
    return result.values;
  } catch {
    return [];
  }
}

/** Writes one config field via `plugin.<plugin_id>.config.set`. Left to
 * throw on failure (unlike the two reads above) — the API route needs to
 * distinguish "saved" from "failed" to answer the client toggle
 * correctly, so this is not the layer that should swallow the error. */
export async function setPluginConfigValue(
  pluginId: string,
  key: string,
  value: boolean,
  token: string
): Promise<void> {
  await invokeCapability(`plugin.${pluginId}.config.set`, { key, value }, token);
}
