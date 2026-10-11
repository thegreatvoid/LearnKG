"""
Downstream: Educational Knowledge Graph Builder
Builds an Educational Knowledge Graph from concepts.csv and relations.csv.
- Nodes: Canonical concepts with definitions, aliases, and types on hover tooltip.
- Edges: Controlled educational relations (Prerequisite, Part-of, Application, Extension, Similarity)
         with educational weights and evidence quotes on hover.
"""

from pathlib import Path
from typing import Optional
import colorsys
import random
import networkx as nx
import pandas as pd
from pyvis.network import Network


# Distinct colors for the 5 educational relation types
RELATION_COLORS = {
    "Prerequisite": "#d90429",   # Bold red/crimson - foundational dependency
    "Part-of":      "#0077b6",   # Deep sapphire - structural composition
    "Application":  "#2a9d8f",   # Teal/emerald - applied function
    "Extension":    "#f4a261",   # Warm amber - conceptual evolution
    "Similarity":   "#7209b7",   # Amethyst purple - symmetric relation
}


def hls_palette(n: int) -> list[str]:
    """Generates perceptually distinct hex colors."""
    colors = []
    for i in range(n):
        hue = i / max(1, n)
        r, g, b = colorsys.hls_to_rgb(hue, 0.55, 0.70)
        colors.append(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
    random.shuffle(colors)
    return colors


def build_educational_graph(
    concepts_csv: Path | str,
    relations_csv: Path | str,
    output_html: Path | str = "./docs/index.html",
    show_edge_labels: bool = False,
    show_edge_tooltips: bool = True,
) -> nx.DiGraph:
    """
    Constructs a NetworkX DiGraph and generates an interactive Pyvis visualization.
    """
    df_concepts = pd.read_csv(concepts_csv, dtype=str).fillna("")
    df_relations = pd.read_csv(relations_csv, dtype=str).fillna("")

    # Mapping concept_id -> Concept Row
    concept_map = {}
    for _, row in df_concepts.iterrows():
        concept_map[row["concept_id"]] = row

    G = nx.DiGraph()

    # Add Nodes
    for cid, row in concept_map.items():
        name = row["concept_name"]
        ctype = row["concept_type"] or "Concept"
        defn = row["definition"]
        aliases = row["aliases"]
        chap = row["chapter"]
        page = row["page"]

        tooltip = f"<b>{name}</b> ({ctype})<br/>"
        if defn:
            tooltip += f"<br/><b>Definition:</b> {defn}<br/>"
        if aliases:
            tooltip += f"<b>Aliases:</b> {aliases}<br/>"
        if chap or page:
            tooltip += f"<small><i>Location:</i> {chap} (Page {page})</small>"

        G.add_node(
            cid,
            label=name,
            title=tooltip,
            concept_name=name,
            concept_type=ctype,
            definition=defn,
        )

    # Add Edges
    for _, row in df_relations.iterrows():
        src_id = row["source_id"]
        tgt_id = row["target_id"]
        rel_type = row["relation_type"]
        weight_val = float(row["weight"]) if row["weight"] else 5.0
        evidence = row["evidence"]

        if src_id not in G.nodes or tgt_id not in G.nodes:
            continue

        src_name = concept_map[src_id]["concept_name"]
        tgt_name = concept_map[tgt_id]["concept_name"]

        edge_attrs = {
            "weight": weight_val,
            "value": weight_val,
            "relation_type": rel_type,
            "color": RELATION_COLORS.get(rel_type, "#888888"),
        }

        if show_edge_tooltips:
            tooltip = f"<b>{src_name}</b> &rarr; <b>{tgt_name}</b><br/>"
            tooltip += f"<b>Relation:</b> {rel_type} (Weight: {int(weight_val)})<br/>"
            if evidence:
                tooltip += f"<i>Evidence:</i> &ldquo;{evidence}&rdquo;"
            edge_attrs["title"] = tooltip

        if show_edge_labels:
            edge_attrs["label"] = rel_type

        G.add_edge(src_id, tgt_id, **edge_attrs)

        # For Similarity, add symmetric edge if not already present
        if rel_type == "Similarity" and not G.has_edge(tgt_id, src_id):
            edge_attrs_rev = dict(edge_attrs)
            if show_edge_tooltips:
                tooltip_rev = f"<b>{tgt_name}</b> &harr; <b>{src_name}</b><br/>"
                tooltip_rev += f"<b>Relation:</b> Similarity (Weight: {int(weight_val)})<br/>"
                if evidence:
                    tooltip_rev += f"<i>Evidence:</i> &ldquo;{evidence}&rdquo;"
                edge_attrs_rev["title"] = tooltip_rev
            G.add_edge(tgt_id, src_id, **edge_attrs_rev)

    # Community detection & node styling
    if G.number_of_nodes() > 0:
        G_undir = G.to_undirected()
        try:
            communities_gen = nx.community.girvan_newman(G_undir)
            _ = next(communities_gen)
            next_level = next(communities_gen)
            communities = sorted(map(sorted, next_level))
        except Exception:
            communities = [[n] for n in G.nodes()]

        palette = hls_palette(len(communities))
        for g_idx, comm in enumerate(communities):
            col = palette[g_idx % len(palette)]
            for nid in comm:
                if nid in G.nodes:
                    G.nodes[nid]["group"] = g_idx + 1
                    G.nodes[nid]["color"] = col

        # PageRank sizing
        try:
            pr = nx.pagerank(G, weight="weight", max_iter=200)
            min_pr = min(pr.values()) if pr else 1.0
            max_pr = max(pr.values()) if pr else 1.0
            rng = max_pr - min_pr if max_pr > min_pr else 1.0
            for nid in G.nodes:
                norm_size = (pr.get(nid, min_pr) - min_pr) / rng
                G.nodes[nid]["size"] = int(12 + norm_size * 45)
        except Exception:
            for nid in G.nodes:
                deg = G.degree(nid)
                G.nodes[nid]["size"] = max(12, min(50, 12 + deg * 4))

    # Render Pyvis Network
    out_file = Path(output_html)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    net = Network(
        notebook=False,
        directed=True,
        cdn_resources="remote",
        height="900px",
        width="100%",
        select_menu=True,
        filter_menu=False,
    )
    net.from_nx(G)

    net.set_options("""
    var options = {
      "edges": {
        "arrows": {
          "to": { "enabled": true, "scaleFactor": 0.7 }
        },
        "smooth": {
          "enabled": true,
          "type": "curvedCW",
          "roundness": 0.15
        },
        "font": {
          "size": 9,
          "align": "middle",
          "strokeWidth": 2,
          "strokeColor": "#ffffff"
        },
        "scaling": { "min": 1, "max": 10 }
      },
      "nodes": {
        "font": { "size": 13, "face": "Arial", "strokeWidth": 2, "strokeColor": "#ffffff" },
        "scaling": { "min": 12, "max": 55 }
      },
      "physics": {
        "forceAtlas2Based": {
          "centralGravity": 0.015,
          "springLength": 130,
          "springConstant": 0.08,
          "damping": 0.4,
          "avoidOverlap": 0.25
        },
        "maxVelocity": 45,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "iterations": 180 }
      }
    }
    """)

    net.write_html(str(out_file))
    print(f"[+] Educational Knowledge Graph HTML generated at: {out_file.resolve()}")
    return G
