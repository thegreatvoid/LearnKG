"""Diagnose prerequisite recall attrition across pipeline stages on the cleaned AL-CPL benchmark.

Usage:
  python scripts/diagnose_recall.py [--kg-dir data_output/ck12_geometry_kgx_v2_hybrid]
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Dict, List, Tuple

import networkx as nx
import pandas as pd

from evaluate_prerequisite_extraction import build_extracted_concept_index, match_gold_concept
from kg_eval.data import (
    CLEANED_ALCPL_PAIRS,
    CLEANED_ALCPL_PREQS,
    DEFAULT_ALCPL_PAIRS,
    DEFAULT_ALCPL_PREQS,
    load_alcpl,
    load_kg,
)


def diagnose(kg_dir: Path, pairs_path: Path = DEFAULT_ALCPL_PAIRS, preqs_path: Path = DEFAULT_ALCPL_PREQS):
    print("=" * 70)
    print(f"LearnKG Prerequisite Recall Diagnostics")
    print(f"KG Directory: {kg_dir}")
    print(f"Pairs Path:   {pairs_path}")
    print(f"Preqs Path:   {preqs_path}")
    print("=" * 70)

    # 1. Load benchmark & concepts
    gold_df = load_alcpl(pairs_path, preqs_path)
    gold_pos = gold_df[gold_df["label"] == 1].reset_index(drop=True)
    concepts, relations = load_kg(kg_dir)
    by_id, term_to_cid, normalizer = build_extracted_concept_index(concepts)

    unique_gold = sorted(set(gold_df["concept"]) | set(gold_df["prereq"]))
    match: Dict[str, Tuple] = {g: match_gold_concept(g, term_to_cid, by_id, normalizer) for g in unique_gold}
    matched_cids = {g: m[0] for g, m in match.items() if m[0]}

    print(f"\n[1] Benchmark & Concept Coverage:")
    print(f"  Total Gold Concept Pairs:          {len(gold_df)}")
    print(f"  Total Gold Positive Pairs:         {len(gold_pos)}")
    print(f"  Unique Gold Concepts:              {len(unique_gold)}")
    print(f"  Gold Concepts Matched to KG:       {len(matched_cids)} / {len(unique_gold)} ({len(matched_cids)/len(unique_gold):.1%})")

    # 2. Pairs with both endpoints extracted
    both_matched = []
    for a, b in zip(gold_pos["concept"], gold_pos["prereq"]):
        ca, cb = match[a][0], match[b][0]
        if ca and cb and ca != cb:
            both_matched.append((a, b, ca, cb))

    n_both = len(both_matched)
    n_pos = len(gold_pos)
    print(f"\n[2] Endpoint Matching Attrition:")
    print(f"  Gold Positives with BOTH concepts extracted: {n_both} / {n_pos} ({n_both/n_pos:.1%})")
    print(f"  Lost due to missing concept endpoints:       {n_pos - n_both} / {n_pos} ({(n_pos - n_both)/n_pos:.1%})")

    # 3. Candidate pool & Scored Pairs
    ps_file = kg_dir / "pair_scores.csv"
    if ps_file.exists():
        ps_df = pd.read_csv(ps_file, dtype=str)
        scored_unordered = {frozenset((s, t)) for s, t in zip(ps_df["source_id"], ps_df["target_id"])}
        in_cands = [x for x in both_matched if frozenset((x[2], x[3])) in scored_unordered]
        print(f"\n[3] Candidate Pool Coverage (pair_scores.csv):")
        print(f"  Gold Positives present in candidate pool:    {len(in_cands)} / {n_both} ({len(in_cands)/n_both:.1%} of matched)")
        print(f"                                               {len(in_cands)} / {n_pos} ({len(in_cands)/n_pos:.1%} end-to-end)")
        
        # Check scores for cb -> ca (prerequisite: B is prerequisite of A)
        ps_float = pd.read_csv(ps_file)
        score_map = {(r["source_id"], r["target_id"]): float(r["score_Prerequisite"]) for _, r in ps_float.iterrows()}
        scores = [score_map.get((cb, ca), 0.0) for a, b, ca, cb in both_matched]
        s_series = pd.Series(scores)
        print(f"\n[4] Prerequisite Score Distribution on Matched Gold Positives:")
        print(f"  Score > 0.00:  {(s_series > 0.00).sum()} / {n_both} ({(s_series > 0.00).mean():.1%})")
        print(f"  Score >= 0.20: {(s_series >= 0.20).sum()} / {n_both} ({(s_series >= 0.20).mean():.1%})")
        print(f"  Score >= 0.50: {(s_series >= 0.50).sum()} / {n_both} ({(s_series >= 0.50).mean():.1%})")
        print(f"  Mean Score:    {s_series.mean():.4f} | Median Score: {s_series.median():.4f}")
    else:
        print(f"\n[3] Candidate Pool: pair_scores.csv not found in {kg_dir} (metric not calculated from saved artifacts).")

    # 4. Final Graph Relations
    prereq_edges = {(r["source_id"], r["target_id"]): float(r["weight"])
                    for _, r in relations[relations["relation_type"] == "Prerequisite"].iterrows()}
    direct_tp = [x for x in both_matched if (x[3], x[2]) in prereq_edges]

    G = nx.DiGraph()
    G.add_edges_from(prereq_edges.keys())
    closure_tp = [x for x in both_matched if x[3] in G and x[2] in G and nx.has_path(G, x[3], x[2])]

    print(f"\n[5] Final Knowledge Graph Recovery:")
    print(f"  Direct Prerequisite TP (1-hop):   {len(direct_tp)}")
    print(f"    - Main Subset Recall:            {len(direct_tp) / n_both:.1%} ({len(direct_tp)} / {n_both})")
    print(f"    - End-to-End Recall:             {len(direct_tp) / n_pos:.1%} ({len(direct_tp)} / {n_pos})")
    print(f"  Transitive Closure TP (path):     {len(closure_tp)}")
    print(f"    - Main Subset Recall:            {len(closure_tp) / n_both:.1%} ({len(closure_tp)} / {n_both})")
    print(f"    - End-to-End Recall:             {len(closure_tp) / n_pos:.1%} ({len(closure_tp)} / {n_pos})")

    # Direction check
    reversed_edges = [x for x in both_matched if (x[2], x[3]) in prereq_edges]
    print(f"  Reversed Prerequisite Edges (A->B): {len(reversed_edges)}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kg-dir", type=Path, default=Path("data_output/ck12_geometry_kgx_v2_hybrid"))
    parser.add_argument("--pairs", type=Path, default=DEFAULT_ALCPL_PAIRS)
    parser.add_argument("--preqs", type=Path, default=DEFAULT_ALCPL_PREQS)
    args = parser.parse_args()
    diagnose(args.kg_dir, args.pairs, args.preqs)
