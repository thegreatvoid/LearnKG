"""
Constructs the localized subgraph around a key concept: a bounded-depth
neighborhood search, split into prerequisites vs. related/supporting
concepts, ranked by edge weight + structural importance + BFS-depth
relevance decay + question keyword overlap, then capped to a concise node
budget (project spec section 18).
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from .concept_matcher import _tokenize
from .kg_adapter import KGNode, KnowledgeGraph

MAX_DEPTH = 2
MAX_PREREQUISITES = 6
MAX_RELATED = 6


@dataclass
class RankedConcept:
    node: KGNode
    relation_type: str
    direction: str  # "prerequisite" | "related"
    depth: int
    score: float


def _bfs_neighborhood(kg: KnowledgeGraph, center_id: str, max_depth: int) -> Dict[str, int]:
    """concept_id -> shortest hop distance from the center, over the
    undirected view of the graph (relation direction is handled separately
    when classifying prerequisite-vs-related)."""
    depths = {center_id: 0}
    frontier = [center_id]
    for depth in range(1, max_depth + 1):
        next_frontier = []
        for nid in frontier:
            for edge in kg.edges_of(nid):
                other = edge.target if edge.source == nid else edge.source
                if other not in depths:
                    depths[other] = depth
                    next_frontier.append(other)
        frontier = next_frontier
    return depths


def build_localized_subgraph(
    kg: KnowledgeGraph,
    center_id: str,
    question_tokens: Set[str],
) -> Tuple[List[RankedConcept], List[RankedConcept]]:
    """Returns (prerequisites, related) ranked concept lists, already capped
    to MAX_PREREQUISITES / MAX_RELATED."""
    depths = _bfs_neighborhood(kg, center_id, MAX_DEPTH)

    candidates: Dict[str, RankedConcept] = {}
    for nid, depth in depths.items():
        if nid == center_id or depth == 0:
            continue
        node = kg.get(nid)
        if node is None:
            continue

        # A pair can carry more than one relation_type (e.g. both "Part-of"
        # and "Prerequisite"); a Prerequisite edge FROM this concept TO the
        # center always wins the classification regardless of which typed
        # edge happens to have the higher weight.
        incoming = kg.edge_types_between(nid, center_id)  # nid -> center
        outgoing = kg.edge_types_between(center_id, nid)  # center -> nid
        all_typed_edges = incoming + outgoing

        is_prereq = any(e.relation_type == "Prerequisite" for e in incoming)
        best_weight = max((e.weight for e in all_typed_edges), default=0.0)
        if is_prereq:
            rel_type = "Prerequisite"
        elif all_typed_edges:
            rel_type = max(all_typed_edges, key=lambda e: e.weight).relation_type
        else:
            rel_type = "related_to"

        name_tokens = _tokenize(node.label)
        keyword_overlap = len(question_tokens & name_tokens) / max(1, len(name_tokens))
        depth_decay = 1.0 / depth

        # pagerank values are small (~0.02-0.09 on a 33-node graph); rescale
        # so it contributes on a comparable footing to the other factors.
        structural_importance = min(1.0, node.pagerank * 10)

        score = (
            0.4 * best_weight
            + 0.25 * structural_importance
            + 0.2 * depth_decay
            + 0.15 * keyword_overlap
        )

        candidates[nid] = RankedConcept(
            node=node,
            relation_type=rel_type,
            direction="prerequisite" if is_prereq else "related",
            depth=depth,
            score=round(score, 4),
        )

    prereqs = sorted(
        (c for c in candidates.values() if c.direction == "prerequisite"),
        key=lambda c: -c.score,
    )[:MAX_PREREQUISITES]
    related = sorted(
        (c for c in candidates.values() if c.direction == "related"),
        key=lambda c: -c.score,
    )[:MAX_RELATED]
    return prereqs, related
