import dagre from "dagre";
import { MarkerType, type Edge, type Node } from "reactflow";
import type { LocalizedGraph } from "../../types/api";

const NODE_WIDTH = 190;
const NODE_HEIGHT = 56;

/**
 * Converts the backend's LocalizedGraph into positioned React Flow
 * nodes/edges using a dagre layout — the graph is small (5-30 nodes) so a
 * one-shot layout on every query response is cheap and keeps the central
 * concept visually anchored relative to its neighbors.
 */
export function layoutGraph(graph: LocalizedGraph): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 90 });
  g.setDefaultEdgeLabel(() => ({}));

  for (const n of graph.nodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const e of graph.edges) {
    g.setEdge(e.source, e.target);
  }

  dagre.layout(g);

  const nodes: Node[] = graph.nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      id: n.id,
      type: "concept",
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      data: { node: n },
    };
  });

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    label: e.type,
    animated: false,
    style: { stroke: "var(--color-border)", strokeWidth: 1.5 },
    labelStyle: { fill: "var(--color-text-muted)", fontSize: 10 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "var(--color-border)" },
  }));

  return { nodes, edges };
}
