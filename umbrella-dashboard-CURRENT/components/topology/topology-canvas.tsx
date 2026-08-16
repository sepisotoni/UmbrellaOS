"use client";

// components/topology/topology-canvas.tsx — the toggle between layers is
// the only interactive state here (Decision 6 scope: a leaf, not a whole
// page defaulting to client). Both layers' data was already fetched
// server-side (lib/topology.ts) and handed in as props — this component
// never talks to the backend itself.
//
// Layout: both layers happen to be a two-tier bipartite graph today (host
// -> server; plugin -> capability), so one simple two-column layout
// covers both without pulling in a force-directed graph library this
// sandbox can't verify installs (no network access — see
// handback/STEP2-DASHBOARD-SCAFFOLD.md). If a layer's shape ever stops
// being bipartite, this is the file to revisit, not force it to fit.
import { useMemo, useState } from "react";
import type { TopologyLayer, TopologyNode } from "@/lib/topology-types";

const ROOT_KINDS = new Set(["host", "plugin"]);
const NODE_WIDTH = 160;
const NODE_HEIGHT = 36;
const ROW_GAP = 52;
const COL_X = { root: 60, leaf: 420 };

const STATUS_COLOR: Record<string, string> = {
  online: "#34d399",
  offline: "#f87171",
  draining: "#fbbf24",
  pending: "#94a3b8",
};

type Positioned = TopologyNode & { x: number; y: number };

function layoutLayer(layer: TopologyLayer): {
  positioned: Positioned[];
  edges: { x1: number; y1: number; x2: number; y2: number }[];
  height: number;
} {
  const roots = layer.nodes.filter((n) => ROOT_KINDS.has(n.kind));
  const leaves = layer.nodes.filter((n) => !ROOT_KINDS.has(n.kind));

  const positioned: Positioned[] = [
    ...roots.map((n, i) => ({ ...n, x: COL_X.root, y: 20 + i * ROW_GAP })),
    ...leaves.map((n, i) => ({ ...n, x: COL_X.leaf, y: 20 + i * ROW_GAP })),
  ];

  const byId = new Map(positioned.map((n) => [n.id, n]));
  const edges = layer.edges
    .map((e) => {
      const source = byId.get(e.source);
      const target = byId.get(e.target);
      if (!source || !target) return null;
      return {
        x1: source.x + NODE_WIDTH,
        y1: source.y + NODE_HEIGHT / 2,
        x2: target.x,
        y2: target.y + NODE_HEIGHT / 2,
      };
    })
    .filter((e): e is NonNullable<typeof e> => e !== null);

  const height = Math.max(roots.length, leaves.length, 1) * ROW_GAP + 40;
  return { positioned, edges, height };
}

export function TopologyCanvas({
  infra,
  dependency,
}: {
  infra: TopologyLayer | null;
  dependency: TopologyLayer | null;
}) {
  const available: { id: "infra" | "dependency"; label: string; layer: TopologyLayer }[] = [];
  if (infra) available.push({ id: "infra", label: "Infrastructure", layer: infra });
  if (dependency) available.push({ id: "dependency", label: "Capability dependencies", layer: dependency });

  const [active, setActive] = useState<"infra" | "dependency">(available[0]?.id ?? "infra");
  const current = available.find((a) => a.id === active) ?? available[0];

  const { positioned, edges, height } = useMemo(
    () => (current ? layoutLayer(current.layer) : { positioned: [], edges: [], height: 0 }),
    [current]
  );

  if (available.length === 0) {
    return <p className="text-sm opacity-60">No topology data available for your role.</p>;
  }

  return (
    <div className="space-y-4">
      {available.length > 1 && (
        <div className="flex gap-1">
          {available.map((a) => (
            <button
              key={a.id}
              onClick={() => setActive(a.id)}
              className={`rounded-md px-3 py-1.5 text-sm ${
                a.id === active ? "bg-white/10" : "opacity-60 hover:opacity-100"
              }`}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      {positioned.length === 0 ? (
        <p className="text-sm opacity-60">Nothing to show in this layer yet.</p>
      ) : (
        <svg
          viewBox={`0 0 ${COL_X.leaf + NODE_WIDTH + 20} ${height}`}
          className="w-full rounded-lg border border-[var(--border)]"
        >
          {edges.map((e, i) => (
            <line
              key={i}
              x1={e.x1}
              y1={e.y1}
              x2={e.x2}
              y2={e.y2}
              stroke="var(--border)"
              strokeWidth={1.5}
            />
          ))}
          {positioned.map((n) => (
            <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
              <rect
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={6}
                fill="#12151a"
                stroke={n.status ? STATUS_COLOR[n.status] ?? "var(--border)" : "var(--border)"}
                strokeWidth={1.5}
              />
              <text
                x={10}
                y={NODE_HEIGHT / 2 + 4}
                fontSize={11}
                fill="var(--foreground)"
                className="select-none"
              >
                {truncate(n.label, 20)}
              </text>
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}

function truncate(s: string, max: number): string {
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}
