// lib/topology.ts — server-only builders for the two toggleable layers.
// Infra layer: Phase 2's node/server hosting data. Dependency layer:
// Phase 8's plugin-registers-capability relationship, the real graph data
// that actually exists in this codebase today (there is no "capability A
// calls capability B" edge anywhere in the registry — see registry/spec.py
// / registry/registry.py; nothing tracks inter-capability calls. What IS
// real and queryable is which installed plugin registered which
// capabilities, via marketplace.install.list's registered_capability_names
// — the same field step 0 already verified live. That relationship is
// what this layer actually renders).
import "server-only";
import { invokeCapability } from "./api";
import type { TopologyLayer } from "./topology-types";
import type { PluginInstall } from "./types";

type NodeResult = { id: string; name: string; status: string };
type ServerResult = { id: string; name: string; node_id: string; status: string };

export async function buildInfraLayer(token: string): Promise<TopologyLayer> {
  const [nodes, servers] = await Promise.all([
    invokeCapability<NodeResult[]>("hosting.node.list", {}, token),
    invokeCapability<ServerResult[]>("hosting.server.list", {}, token),
  ]);

  return {
    nodes: [
      ...nodes.map((n) => ({ id: `host:${n.id}`, label: n.name, kind: "host" as const, status: n.status })),
      ...servers.map((s) => ({
        id: `server:${s.id}`,
        label: s.name,
        kind: "server" as const,
        status: s.status,
      })),
    ],
    edges: servers.map((s) => ({ source: `host:${s.node_id}`, target: `server:${s.id}` })),
  };
}

export async function buildDependencyLayer(token: string): Promise<TopologyLayer> {
  const installs = await invokeCapability<PluginInstall[]>("marketplace.install.list", {}, token);

  const nodes: TopologyLayer["nodes"] = [];
  const edges: TopologyLayer["edges"] = [];
  const seenCapabilities = new Set<string>();

  for (const install of installs) {
    const pluginNodeId = `plugin:${install.plugin_id}`;
    nodes.push({ id: pluginNodeId, label: install.plugin_id, kind: "plugin" });

    for (const capabilityName of install.registered_capability_names) {
      const capNodeId = `capability:${capabilityName}`;
      if (!seenCapabilities.has(capNodeId)) {
        seenCapabilities.add(capNodeId);
        nodes.push({ id: capNodeId, label: capabilityName, kind: "capability" });
      }
      edges.push({ source: pluginNodeId, target: capNodeId });
    }
  }

  return { nodes, edges };
}

/** Fetches only the layers the caller holds permission for; a layer the
 * caller can't see comes back null rather than throwing, so the page can
 * still render whichever layer IS available. */
export async function buildAvailableLayers(
  permissions: string[],
  token: string
): Promise<{ infra: TopologyLayer | null; dependency: TopologyLayer | null }> {
  const canInfra = permissions.includes("hosting.node.view") && permissions.includes("hosting.server.view");
  const canDependency = permissions.includes("marketplace.install.view");

  const [infra, dependency] = await Promise.all([
    canInfra ? buildInfraLayer(token).catch(() => null) : Promise.resolve(null),
    canDependency ? buildDependencyLayer(token).catch(() => null) : Promise.resolve(null),
  ]);

  return { infra, dependency };
}
