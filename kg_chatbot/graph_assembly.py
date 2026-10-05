"""
Shared assembly of a LocalizedGraph (nodes+edges) from a center concept,
its ranked prerequisite/related neighbors, its detected knowledge gaps, and
its hierarchical parent chain. Used by both the normal-query path and each
side of a comparison-query path in main.py, so the two stay consistent.
"""

from typing import List, Set, Tuple

from .hierarchy import ChainNode
from .kg_adapter import KGNode
from .schemas import GraphEdge, GraphNode
from .subgraph_builder import RankedConcept


def assemble_localized_graph(
    center: KGNode,
    prereqs: List[RankedConcept],
    related: List[RankedConcept],
    gap_ids: Set[str],
    parent_chain: List[ChainNode],
) -> Tuple[List[GraphNode], List[GraphEdge]]:
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    seen_node_ids: Set[str] = set()
    seen_edge_keys: Set[Tuple[str, str, str]] = set()

    def add_node(node: GraphNode) -> None:
        # A concept can legitimately appear both in the Part-of hierarchy
        # chain AND in the local 2-hop neighborhood (e.g. an immediate
        # parent that is also flagged as a knowledge gap). Node ids must be
        # unique for the frontend graph canvas, so the first (structurally
        # more significant) occurrence wins; the relation edge is still
        # added either way so the connection isn't lost.
        if node.id in seen_node_ids:
            return
        seen_node_ids.add(node.id)
        nodes.append(node)

    def add_edge(edge: GraphEdge) -> None:
        key = (edge.source, edge.target, edge.type)
        if key in seen_edge_keys:
            return
        seen_edge_keys.add(key)
        edges.append(edge)

    # Hierarchical parent chain: a linear spine, root-first, each node
    # pointing to the next (its child) so the chain reads top -> bottom,
    # ending with an edge into the queried concept itself.
    prev_id = None
    for chain_node in parent_chain:
        add_node(GraphNode(
            id=chain_node.id, label=chain_node.label, description="",
            type="parent", concept_type=chain_node.kind,
        ))
        if prev_id is not None:
            add_edge(GraphEdge(source=prev_id, target=chain_node.id, type="hierarchy", weight=1.0))
        prev_id = chain_node.id
    if prev_id is not None:
        add_edge(GraphEdge(source=prev_id, target=center.id, type="hierarchy", weight=1.0))

    add_node(GraphNode(
        id=center.id, label=center.label, description=center.description,
        type="central", concept_type=center.concept_type,
    ))

    for c in prereqs:
        node_type = "knowledge_gap" if c.node.id in gap_ids else "prerequisite"
        add_node(GraphNode(
            id=c.node.id, label=c.node.label, description=c.node.description,
            type=node_type, concept_type=c.node.concept_type,
        ))
        add_edge(GraphEdge(source=c.node.id, target=center.id, type=c.relation_type, weight=c.score))

    for c in related:
        node_type = "knowledge_gap" if c.node.id in gap_ids else "related"
        add_node(GraphNode(
            id=c.node.id, label=c.node.label, description=c.node.description,
            type=node_type, concept_type=c.node.concept_type,
        ))
        add_edge(GraphEdge(source=center.id, target=c.node.id, type=c.relation_type, weight=c.score))

    return nodes, edges
