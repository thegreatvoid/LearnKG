"""
Format-agnostic loader for the domain knowledge graph.

Wraps concepts.csv / relations.csv / concept_stats.csv into a single
in-memory KnowledgeGraph object that the rest of kg_chatbot depends on.
Node/edge shape mirrors the generic {id, label, description, type} /
{source, target, type} contract from the project spec, so a different KG
source can be plugged in later by writing a new `from_csv`-shaped loader
that produces the same KGNode/KGEdge/networkx.DiGraph — nothing downstream
needs to change.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
import pandas as pd


@dataclass
class KGNode:
    id: str
    label: str
    description: str = ""
    concept_type: str = "Concept"
    aliases: List[str] = field(default_factory=list)
    chapter: str = ""
    section: str = ""
    pagerank: float = 0.0
    degree_centrality: float = 0.0
    betweenness_centrality: float = 0.0
    community: int = 0


@dataclass
class KGEdge:
    source: str
    target: str
    relation_type: str
    weight: float = 0.5
    evidence: str = ""


class KnowledgeGraph:
    """In-memory adapter over the domain KG CSVs plus a networkx.DiGraph
    for traversal."""

    def __init__(self, nodes: Dict[str, KGNode], graph: nx.DiGraph):
        self.nodes = nodes
        self.graph = graph

    @classmethod
    def from_csv(
        cls,
        concepts_csv: Path | str,
        relations_csv: Path | str,
        concept_stats_csv: Optional[Path | str] = None,
    ) -> "KnowledgeGraph":
        df_c = pd.read_csv(concepts_csv, dtype=str).fillna("")
        df_r = pd.read_csv(relations_csv, dtype=str).fillna("")

        stats_by_id: Dict[str, dict] = {}
        stats_path = Path(concept_stats_csv) if concept_stats_csv else None
        if stats_path and stats_path.exists():
            df_s = pd.read_csv(stats_path, dtype=str).fillna("")
            for _, row in df_s.iterrows():
                stats_by_id[row["concept_id"]] = row

        nodes: Dict[str, KGNode] = {}
        for _, row in df_c.iterrows():
            cid = row["concept_id"]
            stats = stats_by_id.get(cid, {})
            aliases = [a.strip() for a in row.get("aliases", "").split(",") if a.strip()]
            nodes[cid] = KGNode(
                id=cid,
                label=row["concept_name"],
                description=row.get("definition", ""),
                concept_type=row.get("concept_type") or "Concept",
                aliases=aliases,
                chapter=row.get("chapter", ""),
                section=row.get("section", ""),
                pagerank=float(stats.get("pagerank") or 0.0),
                degree_centrality=float(stats.get("degree_centrality") or 0.0),
                betweenness_centrality=float(stats.get("betweenness_centrality") or 0.0),
                community=int(stats.get("community") or 0),
            )

        # MultiDiGraph: a (source, target) pair can legitimately carry more
        # than one relation_type (e.g. both "Part-of" and "Prerequisite").
        # Collapsing to a single DiGraph edge and keeping only the
        # highest-weight row would silently destroy Prerequisite edges
        # whenever a same-pair Application/Part-of edge outweighs it —
        # exactly the relation type prerequisite/gap detection depends on.
        G = nx.MultiDiGraph()
        for cid in nodes:
            G.add_node(cid)

        seen_keys = set()
        for _, row in df_r.iterrows():
            src, tgt = row["source_id"], row["target_id"]
            if src not in nodes or tgt not in nodes:
                continue
            rel_type = row["relation_type"]
            dedup_key = (src, tgt, rel_type)
            weight = float(row["weight"]) if row.get("weight") else 0.5

            if dedup_key in seen_keys:
                # Same (source, target, relation_type) repeated — keep the
                # higher-weight/evidence occurrence.
                existing_keys = [
                    k for k in G[src][tgt] if G[src][tgt][k]["relation_type"] == rel_type
                ]
                if existing_keys:
                    k = existing_keys[0]
                    if weight > G[src][tgt][k]["weight"]:
                        G[src][tgt][k].update(weight=weight, evidence=row.get("evidence", ""))
                continue

            seen_keys.add(dedup_key)
            G.add_edge(
                src,
                tgt,
                weight=weight,
                relation_type=rel_type,
                evidence=row.get("evidence", ""),
            )

        return cls(nodes=nodes, graph=G)

    def get(self, concept_id: str) -> Optional[KGNode]:
        return self.nodes.get(concept_id)

    def all_nodes(self) -> List[KGNode]:
        return list(self.nodes.values())

    def edges_of(self, concept_id: str) -> List[KGEdge]:
        """All incident edges (both directions) for a concept, across all
        relation types between any given pair."""
        edges: List[KGEdge] = []
        if concept_id not in self.graph:
            return edges
        for _, tgt, data in self.graph.out_edges(concept_id, data=True):
            edges.append(KGEdge(concept_id, tgt, data["relation_type"], data["weight"], data.get("evidence", "")))
        for src, _, data in self.graph.in_edges(concept_id, data=True):
            edges.append(KGEdge(src, concept_id, data["relation_type"], data["weight"], data.get("evidence", "")))
        return edges

    def edge_types_between(self, source_id: str, target_id: str) -> List[KGEdge]:
        """All relation-typed edges directly from source_id to target_id
        (there may be more than one, e.g. Part-of AND Prerequisite)."""
        if not self.graph.has_edge(source_id, target_id):
            return []
        return [
            KGEdge(source_id, target_id, data["relation_type"], data["weight"], data.get("evidence", ""))
            for data in self.graph[source_id][target_id].values()
        ]
