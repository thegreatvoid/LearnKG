"""
Hierarchical parent-chain construction: "where does this concept sit in the
overall structure of the chapter/textbook?"

The parent relationship is NOT invented — it is derived entirely from the
existing domain KG:

  1. `Part-of` edges are directed sub-component -> whole (see
     relation_extractor.py's pedagogical_rules, e.g. "Sigmoid Function
     --Part-of--> Logistic Regression"). Walking source->target along
     Part-of edges therefore climbs the concept hierarchy one level at a
     time.
  2. Once no further Part-of edge exists, the concept's own `chapter` /
     `section` metadata (already extracted by the pipeline into
     concepts.csv) supplies the remaining, coarser levels of the chain —
     these are synthetic nodes (id `chapter::<name>` / `section::<name>`)
     since chapters/sections are not concept rows themselves.

No LLM is used here: the whole chain is a deterministic graph walk over
data that already exists.
"""

from dataclasses import dataclass
from typing import List, Set

from .kg_adapter import KnowledgeGraph

MAX_CHAIN_DEPTH = 6


@dataclass
class ChainNode:
    id: str
    label: str
    kind: str  # "chapter" | "section" | "concept"


def _best_part_of_parent(kg: KnowledgeGraph, concept_id: str):
    """The highest-weight Part-of edge FROM concept_id (sub -> whole),
    i.e. concept_id's immediate parent in the domain KG, or None.

    kg_adapter doesn't expose a "by relation type" helper, so this scans
    outgoing edges directly rather than extending its public contract for
    a single caller.
    """
    if concept_id not in kg.graph:
        return None
    best = None
    for _, tgt, data in kg.graph.out_edges(concept_id, data=True):
        if data.get("relation_type") == "Part-of":
            if best is None or data["weight"] > best[1]:
                best = (tgt, data["weight"])
    return best[0] if best else None


def build_parent_chain(kg: KnowledgeGraph, concept_id: str) -> List[ChainNode]:
    """Returns the linear ancestor chain root-first, ENDING right before
    `concept_id` itself (the concept remains the focal/central node and is
    not repeated in the chain). Empty list if no hierarchy info exists."""
    chain: List[ChainNode] = []
    visited: Set[str] = {concept_id}

    current = concept_id
    for _ in range(MAX_CHAIN_DEPTH):
        parent_id = _best_part_of_parent(kg, current)
        if parent_id is None or parent_id in visited:
            break
        parent_node = kg.get(parent_id)
        if parent_node is None:
            break
        chain.append(ChainNode(id=parent_id, label=parent_node.label, kind="concept"))
        visited.add(parent_id)
        current = parent_id

    chain.reverse()  # topmost Part-of ancestor first

    # Prepend chapter/section context from whichever concept sits at the
    # top of the Part-of chain (or the queried concept itself if it has no
    # Part-of parent at all).
    root_concept = kg.get(chain[0].id) if chain else kg.get(concept_id)
    if root_concept:
        section = (root_concept.section or "").strip()
        chapter = (root_concept.chapter or "").strip()
        prefix: List[ChainNode] = []
        if section and section.lower() not in {c.label.lower() for c in chain}:
            prefix.append(ChainNode(id=f"section::{section}", label=section, kind="section"))
        if chapter and chapter.lower() not in {section.lower(), *(c.label.lower() for c in chain)}:
            prefix.append(ChainNode(id=f"chapter::{chapter}", label=chapter, kind="chapter"))
        prefix.reverse()  # chapter above section
        chain = prefix + chain

    return chain
