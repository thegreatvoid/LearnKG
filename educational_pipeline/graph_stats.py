"""
Step: Graph Statistics Computation

Precomputes structural statistics over the constructed knowledge graph
(concepts.csv + relations.csv) once, offline, and persists them as the
"Knowledge Graph Repository" cache: concept_stats.csv (per-concept) and
graph_summary.json (graph-level). This lets the Interactive/query-time
phase look up a concept's Structural Importance and Centrality in O(1)
instead of recomputing centrality measures on every user query.
"""

import json
from pathlib import Path
from typing import Tuple

import networkx as nx
import pandas as pd


def _load_graph(concepts_csv: Path | str, relations_csv: Path | str) -> nx.DiGraph:
    """Builds a plain (un-styled) DiGraph from the dataset CSVs, using the
    full relation set (no visualization-side edge filtering)."""
    df_c = pd.read_csv(concepts_csv, dtype=str).fillna("")
    df_r = pd.read_csv(relations_csv, dtype=str).fillna("")

    G = nx.DiGraph()
    for _, row in df_c.iterrows():
        G.add_node(
            row["concept_id"],
            concept_name=row["concept_name"],
            concept_type=row["concept_type"],
        )

    for _, row in df_r.iterrows():
        src, tgt = row["source_id"], row["target_id"]
        if src not in G.nodes or tgt not in G.nodes:
            continue
        w = float(row["weight"]) if row["weight"] else 0.5
        if G.has_edge(src, tgt):
            G[src][tgt]["weight"] = max(G[src][tgt]["weight"], w)
        else:
            G.add_edge(src, tgt, weight=w, relation_type=row["relation_type"])

    return G


def compute_graph_statistics(
    concepts_csv: Path | str,
    relations_csv: Path | str,
    output_dir: Path | str,
) -> Tuple[Path, Path, dict]:
    """
    Computes and persists:
      - Per-concept (concept_stats.csv): PageRank, in/out-degree, degree
        centrality, betweenness centrality, clustering coefficient, and
        community id — the raw ingredients for the Structural Importance
        (I) and Centrality (C) factors in the Coverage Assessment formula.
      - Graph-level (graph_summary.json): node/edge counts, density,
        average degree, average edge weight, connected components,
        community count, and the top-5 concepts by PageRank.

    Returns (concept_stats_csv_path, graph_summary_json_path, summary_dict).
    """
    G = _load_graph(concepts_csv, relations_csv)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    concept_stats_csv = out_path / "concept_stats.csv"
    graph_summary_json = out_path / "graph_summary.json"

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    if n_nodes == 0:
        summary = {"nodes": 0, "edges": 0}
        graph_summary_json.write_text(json.dumps(summary, indent=2))
        pd.DataFrame(columns=["concept_id"]).to_csv(concept_stats_csv, index=False)
        return concept_stats_csv, graph_summary_json, summary

    G_undir = G.to_undirected()

    try:
        pagerank = nx.pagerank(G, weight="weight", max_iter=200)
    except Exception:
        # e.g. scipy not installed — fall back to a cheap proxy
        in_deg_c = nx.in_degree_centrality(G)
        total = sum(in_deg_c.values()) or 1.0
        pagerank = {n: v / total for n, v in in_deg_c.items()}
    degree_centrality = nx.degree_centrality(G_undir)
    try:
        betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True)
    except Exception:
        betweenness = {n: 0.0 for n in G.nodes}
    clustering = nx.clustering(G_undir, weight="weight")

    try:
        communities_gen = nx.community.girvan_newman(G_undir)
        _ = next(communities_gen)
        next_level = next(communities_gen)
        communities = sorted(map(sorted, next_level))
    except Exception:
        communities = [[n] for n in G.nodes()]
    community_of = {n: idx + 1 for idx, comm in enumerate(communities) for n in comm}

    rows = []
    for nid, ndata in G.nodes(data=True):
        rows.append({
            "concept_id": nid,
            "concept_name": ndata.get("concept_name", ""),
            "pagerank": round(pagerank.get(nid, 0.0), 6),
            "in_degree": G.in_degree(nid),
            "out_degree": G.out_degree(nid),
            "degree_centrality": round(degree_centrality.get(nid, 0.0), 6),
            "betweenness_centrality": round(betweenness.get(nid, 0.0), 6),
            "clustering_coefficient": round(clustering.get(nid, 0.0), 6),
            "community": community_of.get(nid, 0),
        })

    df_stats = pd.DataFrame(rows).sort_values("pagerank", ascending=False)
    df_stats.to_csv(concept_stats_csv, index=False, encoding="utf-8")

    avg_degree = sum(dict(G.degree()).values()) / n_nodes
    avg_weight = sum(d["weight"] for _, _, d in G.edges(data=True)) / n_edges if n_edges else 0.0

    summary = {
        "nodes": n_nodes,
        "edges": n_edges,
        "density": round(nx.density(G), 6),
        "avg_degree": round(avg_degree, 4),
        "avg_edge_weight": round(avg_weight, 4),
        "avg_clustering_coefficient": round(nx.average_clustering(G_undir, weight="weight"), 6),
        "weakly_connected_components": nx.number_weakly_connected_components(G),
        "communities": len(communities),
        "top_5_by_pagerank": df_stats.head(5)[["concept_id", "concept_name", "pagerank"]].to_dict("records"),
    }
    graph_summary_json.write_text(json.dumps(summary, indent=2))

    print(f"[+] Graph statistics computed: {n_nodes} nodes, {n_edges} edges, {len(communities)} communities.")
    print(f"    - Concept stats ({len(df_stats)} rows) : {concept_stats_csv}")
    print(f"    - Graph summary               : {graph_summary_json}")

    return concept_stats_csv, graph_summary_json, summary
