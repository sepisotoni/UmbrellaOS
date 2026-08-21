// lib/topology-types.ts — one small, generic node/edge shape shared by
// both toggleable layers (Decision 1: two toggleable layers over one
// canvas, not one mixed graph — so the canvas component only needs to
// know how to draw "nodes + edges" once, and each layer's fetch function
// is what gives that shape different meaning).
export type TopologyNodeKind = "host" | "server" | "plugin" | "capability";

export type TopologyNode = {
  id: string;
  label: string;
  kind: TopologyNodeKind;
  /** Free-form status text for coloring — e.g. a hosting node/server's
   * pending|online|offline|draining, or undefined for plugin/capability
   * nodes (the dependency layer has no runtime status concept). */
  status?: string;
};

export type TopologyEdge = {
  source: string;
  target: string;
};

export type TopologyLayer = {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
};
