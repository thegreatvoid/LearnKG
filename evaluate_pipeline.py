# -*- coding: utf-8 -*-
"""
=============================================================================
  COMPREHENSIVE EVALUATION FRAMEWORK
  Educational Knowledge Graph Pipeline — Cureus Dataset
=============================================================================
Evaluation Categories:
  A. Data Quality & Schema Integrity
  B. Ontology Compliance & Relation Distribution
  C. Concept Quality (coverage, definitions, aliases, normalisation)
  D. Graph Topology & Structural Metrics
  E. Information-Theoretic Metrics (entropy, diversity)
  F. Referential & Weight Integrity
  G. Pipeline Completeness Score (composite)
=============================================================================
"""

import sys
import math
import warnings
from pathlib import Path
from typing import Dict, List

import pandas as pd
import networkx as nx

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

# Configuration
CONCEPTS_CSV  = REPO_ROOT / "data_output" / "cureus" / "concepts.csv"
RELATIONS_CSV = REPO_ROOT / "data_output" / "cureus" / "relations.csv"

VALID_ONTOLOGY_TYPES = {"Prerequisite", "Part-of", "Application", "Extension", "Similarity"}
WEIGHT_MIN, WEIGHT_MAX = 1, 10
EXPECTED_CONCEPT_COLS  = ["concept_id", "concept_name", "aliases", "concept_type",
                           "definition", "chapter", "section", "page", "chunk_id", "evidence"]
EXPECTED_RELATION_COLS = ["relation_id", "source_id", "target_id", "relation_type",
                           "weight", "page", "chunk_id", "evidence"]


def _bar(value: float, width: int = 30) -> str:
    filled = int(round(min(1.0, value) * width))
    return "#" * filled + "." * (width - filled)


def _pct(num: int, denom: int) -> str:
    if denom == 0:
        return "N/A"
    return f"{num}/{denom}  ({num/denom*100:.1f}%)"


def _entropy(counts: List[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts if c > 0)


def section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def subsection(title: str):
    print(f"\n  -- {title}")


def metric(label: str, value, bar: float = None, note: str = ""):
    line = f"    {label:<45} {value}"
    if note:
        line += f"   [{note}]"
    print(line)
    if bar is not None:
        print(f"    {'':>45} {_bar(min(1.0, bar))}")


def load_data():
    df_c = pd.read_csv(CONCEPTS_CSV,  dtype=str).fillna("")
    df_r = pd.read_csv(RELATIONS_CSV, dtype=str).fillna("")
    df_r["weight"] = pd.to_numeric(df_r["weight"], errors="coerce").fillna(0)
    df_r["page"]   = pd.to_numeric(df_r["page"],   errors="coerce").fillna(0)
    df_c["page"]   = pd.to_numeric(df_c["page"],   errors="coerce").fillna(0)

    G = nx.DiGraph()
    for _, row in df_c.iterrows():
        G.add_node(row["concept_id"], **row.to_dict())
    for _, row in df_r.iterrows():
        if row["source_id"] in G.nodes and row["target_id"] in G.nodes:
            G.add_edge(row["source_id"], row["target_id"],
                       weight=float(row["weight"]),
                       relation_type=row["relation_type"],
                       evidence=row["evidence"])
    return df_c, df_r, G


def eval_schema(df_c, df_r):
    results = {}
    section("A. DATA QUALITY & SCHEMA INTEGRITY")

    subsection("CSV existence & row counts")
    metric("concepts.csv exists",  str(CONCEPTS_CSV.exists()))
    metric("relations.csv exists", str(RELATIONS_CSV.exists()))
    metric("Total concepts (rows)", len(df_c))
    metric("Total relations (rows)", len(df_r))

    subsection("Column schema match")
    c_cols_ok = list(df_c.columns) == EXPECTED_CONCEPT_COLS
    r_cols_ok = list(df_r.columns) == EXPECTED_RELATION_COLS
    metric("concepts.csv  columns exact match",  "PASS" if c_cols_ok else "FAIL",
           bar=1.0 if c_cols_ok else 0.0)
    metric("relations.csv columns exact match",  "PASS" if r_cols_ok else "FAIL",
           bar=1.0 if r_cols_ok else 0.0)

    subsection("Null / empty cell analysis")
    for col in ["concept_name", "concept_type", "definition", "chunk_id", "evidence"]:
        null_cnt = (df_c[col] == "").sum()
        metric(f"  concepts['{col}'] empty cells", f"{null_cnt}/{len(df_c)}",
               bar=1 - null_cnt / max(1, len(df_c)))

    for col in ["relation_type", "source_id", "target_id", "weight"]:
        null_cnt = (df_r[col] == "").sum() if col != "weight" else int((df_r["weight"] == 0).sum())
        metric(f"  relations['{col}'] empty/zero cells", f"{null_cnt}/{len(df_r)}",
               bar=1 - null_cnt / max(1, len(df_r)))

    subsection("ID uniqueness")
    dup_c = int(df_c["concept_id"].duplicated().sum())
    dup_r = int(df_r["relation_id"].duplicated().sum())
    metric("Duplicate concept_ids",  dup_c,  bar=1.0 if dup_c == 0 else 0.0, note="ideal=0")
    metric("Duplicate relation_ids", dup_r,  bar=1.0 if dup_r == 0 else 0.0, note="ideal=0")

    schema_score = (c_cols_ok + r_cols_ok + (dup_c == 0) + (dup_r == 0)) / 4
    results.update({"schema_score": schema_score, "n_concepts": len(df_c),
                    "n_relations": len(df_r), "dup_concepts": dup_c, "dup_relations": dup_r,
                    "c_schema_ok": c_cols_ok, "r_schema_ok": r_cols_ok})
    return results


def eval_ontology(df_r):
    results = {}
    section("B. ONTOLOGY COMPLIANCE & RELATION DISTRIBUTION")

    subsection("Controlled-type compliance")
    invalid = set(df_r["relation_type"].unique()) - VALID_ONTOLOGY_TYPES
    compliance = 1.0 if not invalid else 0.0
    metric("All relation_types in 5-type ontology", "PASS" if not invalid else f"FAIL -- {invalid}",
           bar=compliance)

    subsection("Relation type distribution")
    type_counts = df_r["relation_type"].value_counts()
    total = len(df_r)
    for rt in VALID_ONTOLOGY_TYPES:
        cnt = int(type_counts.get(rt, 0))
        pct = cnt / total if total > 0 else 0
        metric(f"  {rt:<15}", f"{cnt:>5}  ({pct*100:5.1f}%)", bar=min(1.0, pct * 3))

    raw_entropy = _entropy([int(type_counts.get(rt, 0)) for rt in VALID_ONTOLOGY_TYPES])
    max_entropy = math.log2(len(VALID_ONTOLOGY_TYPES))
    norm_entropy = raw_entropy / max_entropy if max_entropy > 0 else 0
    metric("Relation-type entropy (norm 0->1)", f"{norm_entropy:.4f}",
           bar=norm_entropy, note="1.0=perfectly balanced")

    subsection("Self-loop detection")
    self_loops = int((df_r["source_id"] == df_r["target_id"]).sum())
    metric("Self-loop relations (source==target)", self_loops,
           bar=1.0 if self_loops == 0 else 0.0, note="ideal=0")

    results.update({"ontology_compliance": compliance, "relation_entropy": norm_entropy,
                    "self_loops": self_loops, "type_counts": type_counts.to_dict()})
    return results


def eval_concepts(df_c):
    results = {}
    section("C. CONCEPT QUALITY METRICS")
    n = len(df_c)

    subsection("Definition coverage")
    with_def = int((df_c["definition"].str.strip() != "").sum())
    def_coverage = with_def / n
    metric("Concepts with non-empty definitions", _pct(with_def, n), bar=def_coverage)

    subsection("Alias / synonym coverage")
    with_alias = int((df_c["aliases"].str.strip() != "").sum())
    alias_coverage = with_alias / n
    metric("Concepts with aliases", _pct(with_alias, n), bar=alias_coverage)

    subsection("Concept type distribution")
    type_dist = df_c["concept_type"].value_counts().to_dict()
    for ct, cnt in type_dist.items():
        metric(f"  {ct}", cnt, bar=cnt / n)
    type_entropy_norm = (_entropy(list(type_dist.values())) /
                         (math.log2(len(type_dist)) if len(type_dist) > 1 else 1))
    metric("Concept-type entropy (normalised)", f"{type_entropy_norm:.4f}",
           bar=type_entropy_norm, note="higher=more diverse typing")

    subsection("Evidence text coverage")
    with_ev = int((df_c["evidence"].str.strip() != "").sum())
    ev_coverage = with_ev / n
    metric("Concepts with grounded evidence", _pct(with_ev, n), bar=ev_coverage)

    subsection("Concept name quality")
    avg_name_len = df_c["concept_name"].str.len().mean()
    short_names = int((df_c["concept_name"].str.len() < 3).sum())
    metric("Average concept name length (chars)", f"{avg_name_len:.1f}")
    metric("Very short concept names (<3 chars)", short_names,
           bar=1.0 - short_names / n, note="ideal=0")

    subsection("Chunk-level traceability")
    with_chunk = int((df_c["chunk_id"].str.strip() != "").sum())
    chunk_trace = with_chunk / n
    metric("Concepts traceable to a chunk_id", _pct(with_chunk, n), bar=chunk_trace)

    concept_score = (def_coverage + alias_coverage + ev_coverage + chunk_trace) / 4
    results.update({"definition_coverage": def_coverage, "alias_coverage": alias_coverage,
                    "evidence_coverage": ev_coverage, "chunk_traceability": chunk_trace,
                    "short_names": short_names, "concept_quality_score": concept_score,
                    "concept_type_entropy": type_entropy_norm})
    return results


def eval_graph(G, df_c):
    results = {}
    section("D. GRAPH TOPOLOGY & STRUCTURAL METRICS")
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    subsection("Basic counts")
    metric("Graph nodes (concepts)", n_nodes)
    metric("Graph edges (relations)", n_edges)
    density = nx.density(G)
    metric("Graph density", f"{density:.6f}", bar=min(1.0, density * 30),
           note="sparse is expected for KGs")

    subsection("Connectivity")
    Gu = G.to_undirected()
    n_cc = nx.number_connected_components(Gu)
    largest_cc = max(nx.connected_components(Gu), key=len) if n_nodes > 0 else set()
    lcc_frac = len(largest_cc) / n_nodes if n_nodes > 0 else 0
    metric("Connected components (undirected)", n_cc, note="fewer=better cohesion")
    metric("Largest CC coverage", _pct(len(largest_cc), n_nodes), bar=lcc_frac)
    isolated = list(nx.isolates(G))
    isolation_rate = len(isolated) / n_nodes if n_nodes > 0 else 0
    metric("Isolated nodes (degree=0)", _pct(len(isolated), n_nodes),
           bar=1.0 - isolation_rate, note="ideal=0")

    subsection("Degree statistics")
    degrees     = [d for _, d in G.degree()]
    in_degrees  = [d for _, d in G.in_degree()]
    out_degrees = [d for _, d in G.out_degree()]

    for vals, label in [(degrees, "Total"), (in_degrees, "In"), (out_degrees, "Out")]:
        if vals:
            avg = sum(vals) / len(vals)
            mx  = max(vals)
            metric(f"  {label} degree -- avg", f"{avg:.2f}")
            metric(f"  {label} degree -- max", mx)

    subsection("Clustering & reciprocity")
    try:
        avg_clust = nx.average_clustering(Gu)
        metric("Avg clustering coefficient", f"{avg_clust:.4f}", bar=avg_clust)
    except Exception:
        avg_clust = 0.0

    try:
        recip = nx.overall_reciprocity(G) if n_edges > 0 else 0.0
        metric("Graph reciprocity", f"{recip:.4f}", bar=recip)
    except Exception:
        recip = 0.0

    subsection("DAG / acyclicity")
    is_dag = nx.is_directed_acyclic_graph(G)
    metric("Is Directed Acyclic Graph (DAG)", "YES" if is_dag else "NO (has cycles)")

    subsection("PageRank (top-10 hub concepts)")
    try:
        pr = nx.pagerank(G, weight="weight", max_iter=300)
        concept_map = dict(zip(df_c["concept_id"], df_c["concept_name"]))
        top10 = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:10]
        for rank, (nid, score) in enumerate(top10, 1):
            cname = concept_map.get(nid, nid)[:40]
            metric(f"  #{rank:>2} {cname}", f"{score:.5f}", bar=min(1.0, score * 20))
        results["top_pagerank"] = [(concept_map.get(nid, nid), score) for nid, score in top10]
    except Exception as e:
        print(f"    PageRank error: {e}")

    subsection("HITS -- Hub & Authority scores (top-5)")
    try:
        hubs, auths = nx.hits(G, max_iter=500)
        concept_map = dict(zip(df_c["concept_id"], df_c["concept_name"]))
        top_hubs  = sorted(hubs.items(),  key=lambda x: x[1], reverse=True)[:5]
        top_auths = sorted(auths.items(), key=lambda x: x[1], reverse=True)[:5]
        print("    Top Hubs (high out-importance):")
        for nid, sc in top_hubs:
            metric(f"      {concept_map.get(nid, nid)[:42]}", f"{sc:.5f}", bar=min(1.0, sc * 10))
        print("    Top Authorities (high in-importance):")
        for nid, sc in top_auths:
            metric(f"      {concept_map.get(nid, nid)[:42]}", f"{sc:.5f}", bar=min(1.0, sc * 10))
    except Exception:
        pass

    graph_score = (lcc_frac * 0.5) + ((1 - isolation_rate) * 0.3) + (avg_clust * 0.2)
    results.update({"graph_score": graph_score, "lcc_coverage": lcc_frac,
                    "isolation_rate": isolation_rate, "clustering": avg_clust,
                    "reciprocity": recip, "avg_degree": sum(degrees)/len(degrees) if degrees else 0})
    return results


def eval_information(df_c, df_r, G):
    results = {}
    section("E. INFORMATION-THEORETIC & SEMANTIC DIVERSITY METRICS")

    subsection("Weight distribution entropy")
    w_counts = df_r["weight"].value_counts().to_dict()
    w_entropy = _entropy([int(v) for v in w_counts.values()])
    max_w_entropy = math.log2(WEIGHT_MAX - WEIGHT_MIN + 1)
    norm_w_entropy = w_entropy / max_w_entropy if max_w_entropy > 0 else 0
    metric("Weight entropy (normalised 0->1)", f"{norm_w_entropy:.4f}",
           bar=norm_w_entropy, note="higher=more varied weights")
    for w, cnt in sorted(w_counts.items()):
        metric(f"  Weight {int(w)}", cnt, bar=cnt / len(df_r))

    subsection("Evidence text richness")
    ev_lens = df_r[df_r["evidence"] != ""]["evidence"].str.len()
    evidence_richness = 0.0
    if len(ev_lens) > 0:
        metric("Avg evidence length (chars)", f"{ev_lens.mean():.1f}")
        metric("Min evidence length (chars)", int(ev_lens.min()))
        metric("Max evidence length (chars)", int(ev_lens.max()))
        unique_ev = int(df_r["evidence"].nunique())
        metric("Unique evidence sentences", _pct(unique_ev, len(df_r)),
               bar=unique_ev / len(df_r))
        evidence_richness = min(1.0, ev_lens.mean() / 200)

    subsection("Concept name diversity (type-token ratio)")
    all_words = " ".join(df_c["concept_name"].str.lower().tolist()).split()
    ttr = len(set(all_words)) / len(all_words) if all_words else 0
    metric("Concept name TTR (unique / total tokens)", f"{ttr:.4f}",
           bar=ttr, note="higher=more lexically diverse")

    subsection("Chunk-level concept density")
    chunk_concept_map = df_c.groupby("chunk_id")["concept_id"].count()
    if len(chunk_concept_map) > 0:
        metric("Chunks contributing concepts", len(chunk_concept_map))
        metric("Avg concepts per chunk", f"{chunk_concept_map.mean():.2f}")
        metric("Max concepts in single chunk", int(chunk_concept_map.max()))

    results.update({"weight_entropy": norm_w_entropy, "evidence_richness": evidence_richness,
                    "concept_ttr": ttr})
    return results


def eval_integrity(df_c, df_r):
    results = {}
    section("F. REFERENTIAL & WEIGHT INTEGRITY")

    concept_ids = set(df_c["concept_id"].unique())
    source_ids  = set(df_r["source_id"].unique())
    target_ids  = set(df_r["target_id"].unique())

    subsection("Referential integrity")
    dangling_src = source_ids - concept_ids
    dangling_tgt = target_ids - concept_ids
    ref_ok = (len(dangling_src) == 0) and (len(dangling_tgt) == 0)
    metric("Dangling source_ids", len(dangling_src),
           bar=1.0 if len(dangling_src) == 0 else 0.0, note="ideal=0")
    metric("Dangling target_ids", len(dangling_tgt),
           bar=1.0 if len(dangling_tgt) == 0 else 0.0, note="ideal=0")
    metric("Referential integrity overall", "PASS" if ref_ok else "FAIL",
           bar=1.0 if ref_ok else 0.0)

    subsection("Weight bounds validation [1-10]")
    in_range = bool(((df_r["weight"] >= WEIGHT_MIN) & (df_r["weight"] <= WEIGHT_MAX)).all())
    metric("All weights in [1, 10]", "PASS" if in_range else "FAIL",
           bar=1.0 if in_range else 0.0)
    metric("Weight mean",    f"{df_r['weight'].mean():.2f}")
    metric("Weight std dev", f"{df_r['weight'].std():.2f}")
    metric("Weight min",     int(df_r['weight'].min()))
    metric("Weight max",     int(df_r['weight'].max()))

    subsection("Duplicate relation triplets (src, tgt, type)")
    dup_triplets = int(df_r.duplicated(subset=["source_id", "target_id", "relation_type"]).sum())
    metric("Duplicate (src, tgt, type) triplets", dup_triplets,
           bar=1.0 if dup_triplets == 0 else 0.0, note="ideal=0")

    integrity_score = (ref_ok + in_range + (dup_triplets == 0)) / 3
    results.update({"referential_integrity": ref_ok, "weight_valid": in_range,
                    "dup_triplets": dup_triplets, "integrity_score": integrity_score})
    return results


def compute_composite(schema, ontology, concept, graph, info, integrity):
    section("G. COMPOSITE PIPELINE QUALITY SCORE")

    weights = {
        "Schema Integrity":       (schema.get("schema_score", 0),          0.15),
        "Ontology Compliance":    (ontology.get("ontology_compliance", 0), 0.20),
        "Concept Quality":        (concept.get("concept_quality_score", 0), 0.20),
        "Graph Structure":        (graph.get("graph_score", 0),             0.20),
        "Referential Integrity":  (integrity.get("integrity_score", 0),    0.15),
        "Relation Entropy":       (ontology.get("relation_entropy", 0),    0.05),
        "Evidence Richness":      (info.get("evidence_richness", 0),       0.05),
    }

    composite = sum(s * w for s, w in weights.values())
    total_w = sum(w for _, w in weights.values())
    composite_norm = composite / total_w

    subsection("Sub-scores breakdown")
    for label, (score, w) in weights.items():
        metric(f"  {label:<35} score={score:.3f}  weight={w:.2f}", "", bar=score)

    print("\n  " + "-" * 66)
    pct_val = composite_norm * 100
    if pct_val >= 80:
        grade, verdict = "A", "EXCELLENT"
    elif pct_val >= 65:
        grade, verdict = "B", "GOOD"
    elif pct_val >= 50:
        grade, verdict = "C", "FAIR"
    else:
        grade, verdict = "D", "NEEDS IMPROVEMENT"

    stars = int(round(composite_norm * 5))
    star_str = "*" * stars + "o" * (5 - stars)

    print(f"\n  COMPOSITE PIPELINE QUALITY SCORE  :  {composite_norm:.4f}  ({pct_val:.1f}%)")
    print(f"  Grade                             :  {grade}  --  {verdict}")
    print(f"  Star rating (out of 5)            :  {star_str}")
    print(f"  Progress                          :  {_bar(composite_norm, width=50)}")

    subsection("Improvement recommendations")
    recs = []
    if concept.get("definition_coverage", 0) < 0.5:
        recs.append("Low definition coverage -- enable LLM mode (use_llm=True) to auto-generate definitions.")
    if concept.get("alias_coverage", 0) < 0.2:
        recs.append("Low alias coverage -- add synonym extraction to the concept normaliser.")
    if graph.get("isolation_rate", 1) > 0.1:
        recs.append("High node isolation -- increase co-occurrence window size or lower chunk overlap threshold.")
    if ontology.get("relation_entropy", 0) < 0.5:
        recs.append("Skewed relation-type distribution -- improve linguistic pattern diversity in ontology rules.")
    if graph.get("lcc_coverage", 0) < 0.6:
        recs.append("Graph is fragmented -- add cross-chunk relation linking to improve connectivity.")
    if concept.get("concept_type_entropy", 0) < 0.3:
        recs.append("Concept types are homogeneous -- extend concept_type classification heuristics.")
    if integrity.get("dup_triplets", 0) > 0:
        recs.append(f"{integrity['dup_triplets']} duplicate triplets found -- review deduplication logic.")

    if recs:
        for i, r in enumerate(recs, 1):
            print(f"    [{i}] {r}")
    else:
        print("    All checks passed -- no critical issues found.")


def main():
    print("\n" + "#" * 70)
    print("  EDUCATIONAL KG PIPELINE -- COMPREHENSIVE EVALUATION")
    print("  Dataset: Cureus (Health Policy in India)")
    print("#" * 70)

    df_c, df_r, G = load_data()

    schema    = eval_schema(df_c, df_r)
    ontology  = eval_ontology(df_r)
    concept   = eval_concepts(df_c)
    graph     = eval_graph(G, df_c)
    info      = eval_information(df_c, df_r, G)
    integrity = eval_integrity(df_c, df_r)

    compute_composite(schema, ontology, concept, graph, info, integrity)

    print("\n" + "=" * 70)
    print("  EVALUATION COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
