"""
Comparison-query support: builds two independent localized subgraphs (each
with its own parent chain) and a KG-grounded comparison summary — generic
for any pair of concepts, never hardcoded to a specific domain pair like
TCP/UDP.
"""

from dataclasses import dataclass
from typing import List, Optional

from .concept_matcher import ConceptMatch, _tokenize, match_concept
from .gap_detector import detect_knowledge_gaps
from .hierarchy import ChainNode, build_parent_chain
from .kg_adapter import KnowledgeGraph
from .subgraph_builder import RankedConcept, build_localized_subgraph


@dataclass
class ComparisonSide:
    match: ConceptMatch
    parent_chain: List[ChainNode]
    prerequisites: List[RankedConcept]
    related: List[RankedConcept]
    knowledge_gaps: list


def build_comparison_side(kg: KnowledgeGraph, phrase: str, conversation) -> Optional[ComparisonSide]:
    match = match_concept(phrase, kg)
    if match is None:
        return None
    tokens = _tokenize(phrase)
    prereqs, related = build_localized_subgraph(kg, match.node.id, tokens)
    gaps = detect_knowledge_gaps(prereqs, related, conversation)
    chain = build_parent_chain(kg, match.node.id)
    return ComparisonSide(match=match, parent_chain=chain, prerequisites=prereqs, related=related, knowledge_gaps=gaps)


def _neighbor_label_set(side: ComparisonSide) -> set:
    return {c.node.label for c in side.prerequisites} | {c.node.label for c in side.related}


def build_comparison_summary(side_a: ComparisonSide, side_b: ComparisonSide) -> List[str]:
    """Generic, KG-grounded bullet lines comparing two concepts — built only
    from what the domain KG actually contains for each side (concept_type,
    definitions, prerequisite/related neighbor sets), so it works the same
    way for TCP vs UDP, CNN vs RNN, or any other pair."""
    a, b = side_a.match.node, side_b.match.node
    lines: List[str] = []

    if a.concept_type and b.concept_type:
        if a.concept_type == b.concept_type:
            lines.append(f"Both {a.label} and {b.label} are classified as {a.concept_type} concepts in this knowledge graph.")
        else:
            lines.append(f"{a.label} is a {a.concept_type}; {b.label} is a {b.concept_type}.")

    if a.description:
        lines.append(f"{a.label}: {a.description.strip()}")
    if b.description:
        lines.append(f"{b.label}: {b.description.strip()}")

    shared = _neighbor_label_set(side_a) & _neighbor_label_set(side_b)
    if shared:
        lines.append(f"Shared context: both connect to {', '.join(sorted(shared)[:5])}.")

    only_a = _neighbor_label_set(side_a) - _neighbor_label_set(side_b)
    if only_a:
        lines.append(f"Distinct to {a.label}: {', '.join(sorted(only_a)[:5])}.")

    only_b = _neighbor_label_set(side_b) - _neighbor_label_set(side_a)
    if only_b:
        lines.append(f"Distinct to {b.label}: {', '.join(sorted(only_b)[:5])}.")

    if not lines:
        lines.append(
            f"Both {a.label} and {b.label} exist in the knowledge graph, but there is not yet enough "
            "extracted context to ground a detailed comparison."
        )
    return lines
