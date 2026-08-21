// components/widgets/fleet-overview.tsx — first-party trusted component
// (Phase 10 closeout, Task 2). Same conventions as
// components/widgets/{stat-pair,status-badge,simple-list}.tsx (plain data
// in, React's normal text-content escaping, no raw HTML) without routing
// through the plugin-widget/render_as dispatch pipeline — this renders
// real `hosting.node.list` / `hosting.server.list` / `hosting.server.stats`
// data directly, grouped node → servers, it isn't a plugin-declared slot.
//
// No 'use client' anywhere here — a manual refresh affordance would just
// be a second way to do what re-navigating to this route already does
// (fresh server-side fetch, no client cache to invalidate); skipped per
// the dispatch's "don't overbuild" instruction for this widget
// specifically.
import type { FleetNode } from "@/lib/fleet";

// Node status vocabulary: services/node_service.py's NodeService
// ("pending" | "online" | "offline").
const NODE_STATUS_COLOR: Record<string, string> = {
  online: "bg-emerald-500/20 text-emerald-400",
  offline: "bg-red-500/20 text-red-400",
  pending: "bg-amber-500/20 text-amber-400",
  unknown: "bg-white/10 text-white/70",
};

// Server status vocabulary: services/daemon_client.py's
// ContainerState.status (Docker-style, confirmed against
// tests/test_hosting_services.py and tests/test_self_healing.py's fakes:
// "running" | "stopped" | "created" | "exited" | "unknown").
const SERVER_STATUS_COLOR: Record<string, string> = {
  running: "bg-emerald-500/20 text-emerald-400",
  created: "bg-amber-500/20 text-amber-400",
  stopped: "bg-white/10 text-white/70",
  exited: "bg-red-500/20 text-red-400",
  unknown: "bg-white/10 text-white/70",
};

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 MB";
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) return `${mb.toFixed(0)} MB`;
  return `${(mb / 1024).toFixed(1)} GB`;
}

function StatusPill({ status, colors }: { status: string; colors: Record<string, string> }) {
  const color = colors[status] ?? colors.unknown;
  return (
    <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${color}`}>{status}</span>
  );
}

export function FleetOverview({ nodes }: { nodes: FleetNode[] }) {
  if (nodes.length === 0) {
    return <p className="text-sm opacity-60">No nodes or servers registered yet.</p>;
  }

  return (
    <div className="space-y-4">
      {nodes.map(({ node, servers }) => (
        <section key={node.id} className="rounded-lg border border-[var(--border)] p-4">
          <div className="mb-3 flex items-center justify-between gap-4">
            <h2 className="text-sm font-medium">{node.name}</h2>
            <StatusPill status={node.status} colors={NODE_STATUS_COLOR} />
          </div>
          {servers.length === 0 ? (
            <p className="text-xs opacity-50">No servers on this node.</p>
          ) : (
            <ul className="divide-y divide-[var(--border)]">
              {servers.map((server) => (
                <li key={server.id} className="flex items-center justify-between gap-4 py-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate">{server.name}</p>
                    <p className="text-xs opacity-50">
                      {server.cpu_cores} vCPU · {formatBytes(server.memory_bytes)} allocated
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    {server.stats && (
                      <span className="text-xs opacity-60">
                        {server.stats.cpu_percent.toFixed(0)}% CPU ·{" "}
                        {formatBytes(server.stats.memory_used_bytes)} used
                      </span>
                    )}
                    <StatusPill status={server.status} colors={SERVER_STATUS_COLOR} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}
