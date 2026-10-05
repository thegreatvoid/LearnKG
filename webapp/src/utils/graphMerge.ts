import type { GraphEdge, GraphNode, LocalizedGraph } from "../types/api";

/**
 * Merges a newly-returned localized graph into the running conversation
 * graph (project spec sections 9-12: the learning map grows across turns
 * instead of being replaced). De-duplicates nodes by id and edges by
 * (source, target, type) so re-asking about the same concept, or two
 * queries sharing a neighbor, never produces duplicate graph elements.
 *
 * On a node id collision the newer node's label/description win (it may
 * carry richer info, e.g. a "parent" node later revisited as a "central"
 * node keeps its more specific incoming type) but "central"/"parent"
 * classifications are never downgraded by a later "related"/"gap" sighting
 * of the same id, since the hierarchy/focus signal is more informative.
 */
const TYPE_PRIORITY: Record<GraphNode["type"], number> = {
  central: 4,
  parent: 3,
  knowledge_gap: 2,
  prerequisite: 2,
  related: 1,
  supporting: 0,
};

export function mergeGraphs(base: LocalizedGraph, addition: LocalizedGraph): LocalizedGraph {
  const nodeById = new Map<string, GraphNode>();
  for (const n of base.nodes) nodeById.set(n.id, n);

  for (const n of addition.nodes) {
    const existing = nodeById.get(n.id);
    if (!existing) {
      nodeById.set(n.id, n);
      continue;
    }
    const keepExistingType = TYPE_PRIORITY[existing.type] >= TYPE_PRIORITY[n.type];
    nodeById.set(n.id, {
      ...n,
      type: keepExistingType ? existing.type : n.type,
      description: n.description || existing.description,
    });
  }

  const edgeByKey = new Map<string, GraphEdge>();
  const keyOf = (e: GraphEdge) => `${e.source}|${e.target}|${e.type}`;
  for (const e of base.edges) edgeByKey.set(keyOf(e), e);
  for (const e of addition.edges) {
    const existing = edgeByKey.get(keyOf(e));
    if (!existing || e.weight > existing.weight) edgeByKey.set(keyOf(e), e);
  }

  return { nodes: Array.from(nodeById.values()), edges: Array.from(edgeByKey.values()) };
}

export function emptyGraph(): LocalizedGraph {
  return { nodes: [], edges: [] };
}
