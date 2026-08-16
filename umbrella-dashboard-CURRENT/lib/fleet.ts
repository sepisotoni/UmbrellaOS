// lib/fleet.ts — server-only data fetching for the fleet overview (Phase
// 10 closeout, Task 2). Backed entirely by existing capabilities
// (capabilities/hosting.py): `hosting.node.list`, `hosting.server.list`,
// and `hosting.server.stats` — no new backend plumbing, per the
// dispatch's "this is a UI-only dispatch" instruction.
//
// Node status (`hosting.node.py`'s NodeService: "pending" | "online" |
// "offline") and server status (services/daemon_client.py's
// ContainerState.status, Docker-style: "running" | "stopped" | "created"
// | "exited" | "unknown") are two different vocabularies — kept separate
// here rather than coerced into one, and neither reuses this app's
// existing StatusBadge component, which is built for a third, narrower
// vocabulary (a plugin capability result shaped as `{ status: "online" |
// "offline" | "degraded" | "unknown" }` — see
// components/widgets/status-badge.tsx). Reusing it here would either
// silently mis-color real node/server statuses or require bending
// StatusBadge's plugin-facing contract to fit a first-party caller;
// components/widgets/fleet-overview.tsx has its own small status-color
// maps instead.
import "server-only";
import { invokeCapability } from "./api";
import type { HostingNode, HostingServer, ServerStats } from "./types";

export async function fetchNodes(token: string): Promise<HostingNode[]> {
  try {
    return await invokeCapability<HostingNode[]>("hosting.node.list", {}, token);
  } catch {
    return [];
  }
}

export async function fetchServers(token: string): Promise<HostingServer[]> {
  try {
    return await invokeCapability<HostingServer[]>("hosting.server.list", {}, token);
  } catch {
    return [];
  }
}

/** One best-effort live stats snapshot. `hosting.server.stats` proxies to
 * that server's node daemon (services/daemon_client.py) — a call for a
 * non-running server, or against a node whose daemon isn't reachable
 * (e.g. this project's own ACLClouds deployment has no daemon layer at
 * all, per PROJECT-PRINCIPLES-AND-WORKING-RULES.md / the master doc's
 * hosting-context section), fails outright rather than returning zeros.
 * Null means "not shown," never a fabricated zero. */
export async function fetchServerStats(serverId: string, token: string): Promise<ServerStats | null> {
  try {
    return await invokeCapability<ServerStats>("hosting.server.stats", { server_id: serverId }, token);
  } catch {
    return null;
  }
}

export type FleetServer = HostingServer & { stats: ServerStats | null };

export type FleetNode = {
  node: HostingNode;
  servers: FleetServer[];
};

const UNKNOWN_NODE_ID = "__unassigned__";

/** Servers grouped by node, with best-effort per-server stats attached.
 * Stats are only fetched for servers reporting "running" — fetching for a
 * stopped/created/unknown server is a guaranteed daemon-error round trip
 * for no payoff, and this is an overview, not the full hosting console
 * (dispatch's own "don't overbuild" instruction). Every server currently
 * on record gets a row even if its node_id doesn't match any listed node
 * (shouldn't happen given the FK, but an overview silently dropping a
 * real server would be worse than one synthetic "Unassigned" bucket). */
export async function buildFleetOverview(token: string): Promise<FleetNode[]> {
  const [nodes, servers] = await Promise.all([fetchNodes(token), fetchServers(token)]);

  const serversWithStats: FleetServer[] = await Promise.all(
    servers.map(async (server) => ({
      ...server,
      stats: server.status === "running" ? await fetchServerStats(server.id, token) : null,
    }))
  );

  const byNode = new Map<string, FleetNode>();
  for (const node of nodes) {
    byNode.set(node.id, { node, servers: [] });
  }

  for (const server of serversWithStats) {
    let entry = byNode.get(server.node_id);
    if (!entry) {
      entry = byNode.get(UNKNOWN_NODE_ID);
      if (!entry) {
        entry = {
          node: {
            id: UNKNOWN_NODE_ID,
            name: "Unassigned",
            daemon_url: "",
            status: "unknown",
            labels: {},
          },
          servers: [],
        };
        byNode.set(UNKNOWN_NODE_ID, entry);
      }
    }
    entry.servers.push(server);
  }

  return Array.from(byNode.values());
}
