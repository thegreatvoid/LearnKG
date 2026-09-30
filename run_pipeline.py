import os
import sys
import uuid
import random
from pathlib import Path
import pandas as pd
import numpy as np
import networkx as nx
from pyvis.network import Network

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Contextual Proximity
# ---------------------------------------------------------------------------

def contextual_proximity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes contextual proximity edges:
    For every pair of nodes that appear in the same chunk, create an additional
    undirected co-occurrence edge.  These are added AFTER the LLM directed edges
    and are given a lower weight (1 per co-occurrence) so they enrich but
    don't dominate the directed graph.

    Returns a DataFrame with columns:
        source, target, chunk_id, count, relationship, weight, description
    """
    # Melt to long form: each row is (chunk_id, node)
    dfg_long = pd.melt(
        df,
        id_vars=["chunk_id"],
        value_vars=["source", "target"],
        value_name="node",
    )
    dfg_long.drop(columns=["variable"], inplace=True)

    # Self-join on chunk_id → every (node_A, node_B) pair in the same chunk
    dfg_wide = pd.merge(dfg_long, dfg_long, on="chunk_id", suffixes=("_1", "_2"))

    # Drop self-loops
    self_loops_drop = dfg_wide[dfg_wide["node_1"] == dfg_wide["node_2"]].index
    dfg2 = dfg_wide.drop(index=self_loops_drop).reset_index(drop=True)

    # Group and count
    dfg2 = (
        dfg2.groupby(["node_1", "node_2"])
        .agg({"chunk_id": [",".join, "count"]})
        .reset_index()
    )
    dfg2.columns = ["source", "target", "chunk_id", "count"]
    dfg2.replace("", np.nan, inplace=True)
    dfg2.dropna(subset=["source", "target"], inplace=True)

    # Only keep pairs that co-occur more than once
    dfg2 = dfg2[dfg2["count"] != 1]

    # Assign proximity metadata
    dfg2["relationship"] = "contextual proximity"
    dfg2["weight"] = dfg2["count"].clip(upper=3).astype(float)  # cap at 3 (low signal)
    dfg2["description"] = "These concepts co-occur in the same text chunk."
    return dfg2


# ---------------------------------------------------------------------------
# Community → Color mapping
# ---------------------------------------------------------------------------

def colors2Community(communities, palette="hls") -> pd.DataFrame:
    """Maps communities to distinct hex colors via Seaborn palette."""
    p = sns.color_palette(palette, len(communities)).as_hex()
    random.shuffle(p)
    rows = []
    group = 0
    for community in communities:
        color = p.pop()
        group += 1
        for node in community:
            rows.append({"node": node, "color": color, "group": group})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main Pipeline
import argparse
from educational_pipeline import run_educational_pipeline


def run_pipeline(
    data_dir="cureus",
    pipeline_type="educational",
    regenerate=False,
    model="zephyr:latest",
    use_llm=True,
    output_html="./docs/index.html",
    show_edge_labels=False,
    show_edge_tooltips=True,
    max_edge_label_length=30,
):
    if pipeline_type == "educational":
        print(f"[*] Launching Educational Dataset Construction Pipeline for '{data_dir}'...")
        return run_educational_pipeline(
            data_dir=data_dir,
            model=model,
            use_llm=use_llm,
            output_html=output_html,
            show_edge_labels=show_edge_labels,
            show_edge_tooltips=show_edge_tooltips,
        )

    print(f"[*] Starting Legacy Knowledge Graph Pipeline for dataset: '{data_dir}'...")

    try:
        from langchain.document_loaders import DirectoryLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from helpers.df_helpers import documents2Dataframe, df2Graph, graph2Df
        import seaborn as sns
    except ImportError as e:
        raise ImportError(f"Legacy pipeline requires langchain and seaborn: {e}")

    inputdirectory = Path(f"./data_input/{data_dir}")
    outputdirectory = Path(f"./data_output/{data_dir}")
    outputdirectory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load Documents
    # ------------------------------------------------------------------
    print(f"[*] Loading documents from {inputdirectory}...")
    documents = []
    for file_path in inputdirectory.rglob("*"):
        if file_path.is_file():
            if file_path.suffix.lower() == ".pdf":
                print(f"    - Loading PDF: {file_path.name}")
                loader = PyPDFLoader(str(file_path))
                documents.extend(loader.load())
            elif file_path.suffix.lower() == ".txt":
                print(f"    - Loading TXT: {file_path.name}")
                loader = TextLoader(str(file_path))
                documents.extend(loader.load())
    print(f"[+] Loaded {len(documents)} document chunk(s).")

    # ------------------------------------------------------------------
    # 2. Text Splitting
    # ------------------------------------------------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=150,
        length_function=len,
        is_separator_regex=False,
    )
    pages = splitter.split_documents(documents)
    print(f"[+] Document split into {len(pages)} chunks.")

    # ------------------------------------------------------------------
    # 3. Chunks → DataFrame
    # ------------------------------------------------------------------
    df = documents2Dataframe(pages)
    print(f"[+] Chunks DataFrame shape: {df.shape}")

    # ------------------------------------------------------------------
    # 4. Extract Directed Relations via LLM  (new schema)
    #    Columns: source, target, relationship, weight, description, chunk_id
    # ------------------------------------------------------------------
    graph_csv_path = outputdirectory / "graph.csv"

    if regenerate:
        print(
            f"[*] Extracting directed relations with Ollama model '{model}' "
            f"(this may take a few minutes)..."
        )
        concepts_list = df2Graph(df, model=model)
        dfg1 = graph2Df(concepts_list)
        dfg1.to_csv(graph_csv_path, sep="|", index=False)
        df.to_csv(outputdirectory / "chunks.csv", sep="|", index=False)
        print(f"[+] Directed graph saved to {graph_csv_path}")
    else:
        if graph_csv_path.exists():
            print(f"[*] Loading precomputed graph from {graph_csv_path}...")
            dfg1 = pd.read_csv(graph_csv_path, sep="|")

            # --- Back-compat: remap old node_1/node_2/edge schema if needed ---
            if "node_1" in dfg1.columns and "source" not in dfg1.columns:
                print("[!] Detected old (undirected) graph.csv schema — remapping columns.")
                dfg1 = dfg1.rename(columns={"node_1": "source", "node_2": "target", "edge": "relationship"})
                dfg1["weight"] = dfg1.get("count", pd.Series(4, index=dfg1.index)).clip(1, 10).astype(float)
                dfg1["description"] = ""
        else:
            print(f"[!] No precomputed graph found. Extracting via LLM model '{model}'...")
            concepts_list = df2Graph(df, model=model)
            dfg1 = graph2Df(concepts_list)
            dfg1.to_csv(graph_csv_path, sep="|", index=False)
            df.to_csv(outputdirectory / "chunks.csv", sep="|", index=False)

    # Sanitize
    dfg1.replace("", np.nan, inplace=True)
    dfg1.dropna(subset=["source", "target", "relationship"], inplace=True)
    print(f"[+] Direct LLM directed relations shape: {dfg1.shape}")

    # ------------------------------------------------------------------
    # 5. Contextual Proximity (co-occurrence) edges
    # ------------------------------------------------------------------
    print("[*] Calculating contextual proximity...")
    dfg2 = contextual_proximity(dfg1)
    print(f"[+] Contextual proximity relations shape: {dfg2.shape}")

    # ------------------------------------------------------------------
    # 6. Merge: LLM directed edges + proximity edges
    #    Aggregate: sum weights, concatenate chunk_ids and descriptions
    # ------------------------------------------------------------------
    print("[*] Merging direct and contextual relations...")
    dfg = pd.concat([dfg1, dfg2], axis=0, ignore_index=True)
    dfg = (
        dfg.groupby(["source", "target"])
        .agg(
            chunk_id=("chunk_id", ",".join),
            relationship=("relationship", ",".join),
            weight=("weight", "sum"),      # summed raw weight
            description=("description", lambda x: " | ".join(x.dropna().astype(str))),
        )
        .reset_index()
    )
    print(f"[+] Total merged directed graph edges: {len(dfg)}")

    # ------------------------------------------------------------------
    # 7. Build Directed NetworkX DiGraph
    # ------------------------------------------------------------------
    print("[*] Building NetworkX DiGraph...")
    G = nx.DiGraph()

    # Add all unique nodes
    all_nodes = pd.concat([dfg["source"], dfg["target"]], axis=0).unique()
    for node in all_nodes:
        G.add_node(str(node))

    # Add directed weighted edges
    for _, row in dfg.iterrows():
        edge_attrs = {
            "weight": float(row["weight"]),
            "value":  float(row["weight"]),
        }
        if show_edge_tooltips:
            tooltip = str(row["description"]).strip()
            if not tooltip and "relationship" in row:
                tooltip = str(row["relationship"]).strip()
            if tooltip:
                edge_attrs["title"] = tooltip

        if show_edge_labels:
            rel = str(row["relationship"]).split(",")[0].strip()
            if max_edge_label_length and len(rel) > max_edge_label_length:
                rel = rel[:max_edge_label_length].strip() + "..."
            edge_attrs["label"] = rel

        G.add_edge(
            str(row["source"]),
            str(row["target"]),
            **edge_attrs,
        )

    print(f"[+] DiGraph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

    # ------------------------------------------------------------------
    # 8. Community Detection (on undirected projection for coloring)
    # ------------------------------------------------------------------
    print("[*] Detecting communities (undirected projection for Girvan-Newman)...")
    G_undirected = G.to_undirected()
    communities_generator = nx.community.girvan_newman(G_undirected)
    _ = next(communities_generator)
    next_level_communities = next(communities_generator)
    communities = sorted(map(sorted, next_level_communities))
    print(f"[+] Detected {len(communities)} communities.")

    # ------------------------------------------------------------------
    # 9. Node Attributes: Color (community) + Size (PageRank)
    # ------------------------------------------------------------------
    colors = colors2Community(communities)

    # PageRank on the directed graph — higher rank = more influential node
    try:
        pagerank = nx.pagerank(G, weight="weight", max_iter=200)
    except nx.PowerIterationFailedConvergence:
        print("[!] PageRank did not converge — falling back to in-degree centrality.")
        in_deg = nx.in_degree_centrality(G)
        pagerank = in_deg

    for _, row in colors.iterrows():
        node = row["node"]
        if node in G.nodes:
            G.nodes[node]["group"] = row["group"]
            G.nodes[node]["color"] = row["color"]
            # Scale size: PageRank typically ~0.001-0.05, scale to 10-60px
            G.nodes[node]["size"] = max(10, int(pagerank.get(node, 0) * 1000))

    # ------------------------------------------------------------------
    # 10. Generate Pyvis Interactive Directed Visualization
    # ------------------------------------------------------------------
    output_html_path = Path(output_html)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[*] Rendering directed interactive HTML visualization to {output_html}...")

    net = Network(
        notebook=False,
        directed=True,              # ← enables arrowheads
        cdn_resources="remote",
        height="900px",
        width="100%",
        select_menu=True,
        filter_menu=False,
    )
    net.from_nx(G)

    # Configure edge arrows and curve style for directed clarity
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
          "align": "middle"
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "centralGravity": 0.015,
          "springLength": 100,
          "springConstant": 0.08,
          "damping": 0.4,
          "avoidOverlap": 0
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "iterations": 150 }
      }
    }
    """)

    # net.show_buttons(filter_=["physics"])
    net.write_html(str(output_html_path))
    print(
        f"[SUCCESS] Directed Knowledge Graph generated at: {output_html_path.resolve()}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Knowledge Graph Construction Pipeline")
    parser.add_argument("--pipeline", choices=["educational", "legacy"], default="educational", help="Pipeline type")
    parser.add_argument("--dataset", default="cureus", help="Dataset folder name in data_input/")
    parser.add_argument("--model", default="zephyr:latest", help="Ollama model name")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM extraction")
    parser.add_argument("--show-edge-labels", action="store_true", help="Show edge labels in HTML")
    args = parser.parse_args()

    run_pipeline(
        data_dir=args.dataset,
        pipeline_type=args.pipeline,
        model=args.model,
        use_llm=not args.no_llm,
        show_edge_labels=args.show_edge_labels,
    )
