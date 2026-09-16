"""
Standalone script — regenerates docs/index.html from precomputed graph.csv
as a DIRECTED, WEIGHTED knowledge graph.

Zero scipy / seaborn dependencies:
  - Colors via Python stdlib colorsys (no seaborn)
  - PageRank via nx.pagerank_numpy (no scipy)

Run from the knowledge_graph folder:
    python run_directed.py
"""
import sys
import subprocess
#

# ─────────────────────────────────────────────────────────────────────────────
# Auto-install only what's strictly needed
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED = {
    "pandas":   "pandas",
    "numpy":    "numpy",
    "networkx": "networkx",
    "pyvis":    "pyvis",
}

print("[*] Checking dependencies ...")
for import_name, pip_name in REQUIRED.items():
    try:
        __import__(import_name)
        print(f"    [ok] {pip_name}")
    except ImportError:
        print(f"    [!] '{pip_name}' not found — installing ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "-q"])
        print(f"    [+] '{pip_name}' installed.")

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────
import random
import colorsys       # stdlib — no scipy / seaborn needed
from pathlib import Path

import pandas as pd
import numpy as np
import networkx as nx
from pyvis.network import Network
from helpers.df_helpers import ahp_edge_weight

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def hls_palette(n: int, shuffle: bool = True) -> list[str]:
    """Generate n perceptually-spaced hex colors using HLS (no seaborn needed)."""
    colors = []
    for i in range(n):
        hue = i / n                  # evenly spaced hues 0.0 → 1.0
        r, g, b = colorsys.hls_to_rgb(hue, 0.55, 0.75)   # lightness=0.55, sat=0.75
        colors.append("#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255)))
    if shuffle:
        random.shuffle(colors)
    return colors


def safe_pagerank(G: nx.DiGraph) -> tuple[dict, str]:
    """
    Compute PageRank with three-tier fallback (all numpy-based — no scipy):
      1. nx.pagerank_numpy   (dense numpy eigenvector solve — no scipy)
      2. nx.pagerank         pure-python power iteration (no scipy import path)
      3. nx.in_degree_centrality  (last resort)
    """
    # Tier 1: numpy eigenvector — fast, no scipy
    try:
        pr = nx.pagerank_numpy(G, weight="weight")
        return pr, "PageRank (numpy eigenvector)"
    except Exception as e:
        print(f"    [!] pagerank_numpy failed: {e}")

    # Tier 2: pure-Python power iteration
    try:
        pr = nx.pagerank(G, weight="weight", max_iter=500, tol=1e-5)
        return pr, "PageRank (power iteration)"
    except Exception as e:
        print(f"    [!] pagerank power-iter failed: {e}")

    # Tier 3: in-degree centrality
    pr = nx.in_degree_centrality(G)
    return pr, "in-degree centrality"


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
GRAPH_CSV   = Path("./data_output/cureus/graph.csv")
OUTPUT_HTML = Path("./docs/index.html")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load precomputed graph.csv  (supports old AND new schema)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[*] Loading {GRAPH_CSV} ...")
dfg1 = pd.read_csv(GRAPH_CSV, sep="|")
print(f"[+] Loaded {len(dfg1)} rows.  Columns: {list(dfg1.columns)}")

# Back-compat: remap old node_1/node_2/edge → source/target/relationship
if "node_1" in dfg1.columns and "source" not in dfg1.columns:
    print("[!] Old schema detected — remapping node_1/node_2/edge → source/target/relationship.")
    dfg1 = dfg1.rename(columns={
        "node_1": "source",
        "node_2": "target",
        "edge":   "relationship",
    })
    if "count" in dfg1.columns:
        dfg1["weight"] = pd.to_numeric(dfg1["count"], errors="coerce").fillna(4).clip(1, 10).astype(float)
    else:
        dfg1["weight"] = 4.0
    dfg1["description"] = ""

# Ensure required columns exist
if "weight" not in dfg1.columns:
    dfg1["weight"] = 4.0
else:
    dfg1["weight"] = pd.to_numeric(dfg1["weight"], errors="coerce").fillna(4).clip(1, 10).astype(float)

if "description" not in dfg1.columns:
    dfg1["description"] = ""

# Sanitize
dfg1.replace("", np.nan, inplace=True)
dfg1.dropna(subset=["source", "target", "relationship"], inplace=True)
dfg1["source"]       = dfg1["source"].astype(str).str.strip().str.lower()
dfg1["target"]       = dfg1["target"].astype(str).str.strip().str.lower()
dfg1["relationship"] = dfg1["relationship"].astype(str).str.strip().str.lower()

print(f"[+] Clean directed relations : {len(dfg1)}")
print(f"    Weight range             : {dfg1['weight'].min():.1f} – {dfg1['weight'].max():.1f}")
print(f"    Sample (top 5 by weight):")
print(dfg1[["source","target","relationship","weight"]]
      .sort_values("weight", ascending=False).head(5).to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# 2. Contextual Proximity Edges
#    Concepts co-occurring in the same chunk → weak directed co-occurrence edge.
#    Weight = co-occurrence count, capped at 3 (low-signal signal).
# ─────────────────────────────────────────────────────────────────────────────
print("\n[*] Computing contextual proximity edges ...")
dfg_long = pd.melt(
    dfg1,
    id_vars=["chunk_id"],
    value_vars=["source", "target"],
    value_name="node",
)
dfg_long.drop(columns=["variable"], inplace=True)
dfg_long.dropna(subset=["node", "chunk_id"], inplace=True)

dfg_wide = pd.merge(dfg_long, dfg_long, on="chunk_id", suffixes=("_1", "_2"))
self_loops = dfg_wide[dfg_wide["node_1"] == dfg_wide["node_2"]].index
dfg2 = dfg_wide.drop(index=self_loops).reset_index(drop=True)

dfg2 = (
    dfg2.groupby(["node_1", "node_2"])
    .agg({"chunk_id": [",".join, "count"]})
    .reset_index()
)
dfg2.columns = ["source", "target", "chunk_id", "count"]
dfg2.replace("", np.nan, inplace=True)
dfg2.dropna(subset=["source", "target"], inplace=True)
dfg2 = dfg2[dfg2["count"] > 1]
dfg2["relationship"] = "contextual proximity"
dfg2["weight"]       = dfg2["count"].clip(upper=3).astype(float)
dfg2["description"]  = "Co-occurring concepts in the same text chunk."
print(f"[+] Proximity edges: {len(dfg2)}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Merge LLM-direct + Proximity  →  one row per (source, target) pair
#    Then compute AHP edge weight: 0.52·S + 0.24·C + 0.09·P + 0.15·E
# ─────────────────────────────────────────────────────────────────────────────
print("[*] Merging direct + contextual edges ...")

# Build a lookup: node → set of chunk_ids it appears in (for proximity P)
_node_chunks: dict[str, set] = {}
for col in ["source", "target"]:
    for _, row in dfg1.iterrows():
        node = str(row[col])
        chunks = set(str(row.get("chunk_id", "")).split(",")) - {""}
        _node_chunks.setdefault(node, set()).update(chunks)

# Also note co-occurrence counts per (source, target) from proximity edges
_cooc_count: dict[tuple, float] = {
    (str(r["source"]), str(r["target"])): float(r["count"])
    for _, r in dfg2.iterrows()
}

dfg = pd.concat([dfg1, dfg2], axis=0, ignore_index=True)
dfg = (
    dfg.groupby(["source", "target"])
    .agg(
        chunk_id    =("chunk_id",     lambda x: ",".join(x.dropna().astype(str))),
        relationship=("relationship", lambda x: " | ".join(x.dropna().unique())),
        llm_weight  =("weight",       "max"),   # best LLM score for this pair
        description =("description",  lambda x: " | ".join(x.dropna().astype(str).unique())),
    )
    .reset_index()
)

# ── Compute AHP weight per edge ──────────────────────────────────────────────
def _ahp_row(row) -> float:
    src, tgt = str(row["source"]), str(row["target"])

    # S — semantic similarity: LLM weight (1-10), already in llm_weight col
    S_raw = float(row["llm_weight"])

    # C — co-occurrence count (0 if no proximity edge exists)
    C_raw = _cooc_count.get((src, tgt), 0.0)

    # P — chapter proximity proxy: Jaccard overlap of node chunk sets
    chunks_src = _node_chunks.get(src, set())
    chunks_tgt = _node_chunks.get(tgt, set())
    union  = chunks_src | chunks_tgt
    P_raw = len(chunks_src & chunks_tgt) / len(union) if union else 0.0

    # E — educational context: derived from relationship predicate
    return ahp_edge_weight(S_raw, C_raw, P_raw, row["relationship"])

dfg["weight"] = dfg.apply(_ahp_row, axis=1)

# Scale AHP score (0-1) → display weight (1-10) for Pyvis edge thickness
dfg["weight_display"] = (dfg["weight"] * 9 + 1).round(2)

print(f"[+] Total merged directed edges : {len(dfg)}")
print(f"    AHP weight range (0–1)      : {dfg['weight'].min():.3f} – {dfg['weight'].max():.3f}")
print(f"    Display weight range (1–10) : {dfg['weight_display'].min():.1f} – {dfg['weight_display'].max():.1f}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Build nx.DiGraph  (DIRECTED + WEIGHTED)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[*] Building nx.DiGraph ...")
G = nx.DiGraph()

all_nodes = pd.concat([dfg["source"], dfg["target"]], axis=0).unique()
for node in all_nodes:
    G.add_node(str(node))

for _, row in dfg.iterrows():
    G.add_edge(
        str(row["source"]),
        str(row["target"]),
        title  = f"AHP: {row['weight']:.3f} | {row['description']}",
        label  = f"{row['weight']:.2f}",    # AHP score on arrow
        weight = float(row["weight_display"]),
        value  = float(row["weight_display"]),  # Pyvis uses 'value' for thickness
    )

print(f"[+] DiGraph: {G.number_of_nodes()} nodes,  {G.number_of_edges()} directed edges.")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Community Detection  (Girvan-Newman on undirected projection)
# ─────────────────────────────────────────────────────────────────────────────
print("[*] Detecting communities via Girvan-Newman ...")
G_undir = G.to_undirected()
gen          = nx.community.girvan_newman(G_undir)
_            = next(gen)
next_level   = next(gen)
communities  = sorted(map(sorted, next_level))
print(f"[+] Detected {len(communities)} communities.")

# ─────────────────────────────────────────────────────────────────────────────
# 6. PageRank (scipy-free) + Community Colors
# ─────────────────────────────────────────────────────────────────────────────
print("[*] Computing PageRank for node sizing ...")
pagerank, pr_source = safe_pagerank(G)
pr_vals  = list(pagerank.values())
pr_min   = min(pr_vals)
pr_max   = max(pr_vals)
pr_range = pr_max - pr_min if pr_max > pr_min else 1.0
print(f"    {pr_source}: {pr_min:.5f} – {pr_max:.5f}")

# Generate community colors (no seaborn — pure stdlib)
palette = hls_palette(len(communities), shuffle=True)

# Map nodes → community group + color + PageRank size
node_community = {}
for g_idx, community in enumerate(communities):
    color = palette[g_idx % len(palette)]
    for node in community:
        node_community[node] = {"group": g_idx + 1, "color": color}

for node in G.nodes():
    meta  = node_community.get(node, {"group": 0, "color": "#aaaaaa"})
    pr    = pagerank.get(node, pr_min)
    normalized = (pr - pr_min) / pr_range
    G.nodes[node]["group"] = meta["group"]
    G.nodes[node]["color"] = meta["color"]
    G.nodes[node]["size"]  = int(10 + normalized * 50)   # 10–60 px

# ─────────────────────────────────────────────────────────────────────────────
# 7. Pyvis Directed Visualization
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
print(f"[*] Rendering directed graph → {OUTPUT_HTML} ...")

net = Network(
    notebook       = False,
    directed       = True,           # ← arrowheads
    cdn_resources  = "remote",
    height         = "900px",
    width          = "100%",
    select_menu    = True,
    filter_menu    = False,
)
net.from_nx(G)

net.set_options("""
var options = {
  "configure": {
    "enabled": true,
    "filter": ["physics"]
  },
  "edges": {
    "arrows": {
      "to": { "enabled": true, "scaleFactor": 0.7 }
    },
    "smooth": {
      "enabled": true,
      "type": "curvedCW",
      "roundness": 0.1
    },
    "font": {
      "size": 10,
      "align": "middle",
      "strokeWidth": 2,
      "strokeColor": "#ffffff"
    },
    "scaling": { "min": 1, "max": 8 }
  },
  "nodes": {
    "font": { "size": 12 },
    "scaling": { "min": 10, "max": 50 }
  },
  "physics": {
    "forceAtlas2Based": {
      "centralGravity": 0.003,
      "springLength": 250,
      "springConstant": 0.04,
      "damping": 0.5,
      "avoidOverlap": 1.0
    },
    "maxVelocity": 60,
    "solver": "forceAtlas2Based",
    "timestep": 0.35,
    "stabilization": { "iterations": 300 }
  }
}
""")

net.write_html(str(OUTPUT_HTML))

# ─────────────────────────────────────────────────────────────────────────────
# 8. Verification Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*62}")
print("  ✅  SUCCESS")
print(f"{'='*62}")
print(f"  Output      : {OUTPUT_HTML.resolve()}")
print(f"  Graph type  : DIRECTED  (nx.DiGraph)")
print(f"  Nodes       : {G.number_of_nodes()}")
print(f"  Edges       : {G.number_of_edges()} directed edges")
print(f"  Communities : {len(communities)}")
print(f"  Node sizing : {pr_source}")
print(f"  Weights     : ✅  AHP Formula  0.52·S + 0.24·C + 0.09·P + 0.15·E")
print(f"  AHP range   : {dfg['weight'].min():.3f} – {dfg['weight'].max():.3f}  (0–1 normalised)")
print(f"  Arrowheads  : ✅  enabled  (arrows.to in Pyvis options)")
print(f"  Edge labels : ✅  AHP score on each edge")
print(f"  Colors via  : colorsys stdlib  (no seaborn / scipy)")
print(f"{'='*62}")
print("\n  Top 10 highest-weight directed edges (by AHP score):")
top10 = dfg[["source","target","relationship","weight"]].sort_values("weight", ascending=False).head(10)
for _, r in top10.iterrows():
    rel = r["relationship"].split("|")[0].strip()[:35]
    print(f"    {r['weight']:.3f}  {r['source']!r:35s}  →  {r['target']!r:35s}  [{rel}]")
print()
