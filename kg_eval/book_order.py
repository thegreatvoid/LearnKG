"""
Section 2: agreement of KG relation directions with the textbook's teaching order (no LLM, no annotation).

A textbook introduces prerequisites first, so for a Prerequisite edge source -> target the
source should be first mentioned before the target. Positions are the first whole-word
mention (name or alias, plural tolerant) of each concept in the textbook; this avoids the
chapter labels in concepts.csv, which are inconsistent.

Reported at two granularities:
  char     first-mention character offset (ties only when one name starts the other's mention)
  section  numbered section of the first mention (e.g. 1.2); same section = tie

Metrics:
  forward_rate      per relation type: forward / (forward + backward), with bootstrap CI and a
                    two-sided binomial test against 0.5 (= random direction)
  closure_agreement over all pairs u ~> v connected by Prerequisite paths
  kendall_tau_b     prerequisite depth (longest path from a root) vs first-mention position
  weight_auc        does a higher weight mean "more likely forward"? (Prerequisite edges)
  gold_reference    the same forward rate for AL-CPL gold prerequisites: the realistic ceiling
                    (how often true prerequisites are taught first in THIS book)

Prerequisite edges should point forward (source taught first). Extension is defined by the
pipeline (relation_extractor.py, helpers/prompts.py) as "source builds upon / extends target",
so Extension edges should point BACKWARD. The other types have no expected direction.

Run from LearnKG/:
  python -m kg_eval.book_order [--kg-dir data_output/ck12_geometry] [--out DIR]
"""

import argparse
import json
from pathlib import Path

import networkx as nx
import pandas as pd
from scipy.stats import binomtest, kendalltau

from .data import (
    DEFAULT_KG_DIR,
    DEFAULT_SOURCE,
    auc,
    bootstrap_ci,
    concept_terms,
    first_position,
    fmt,
    load_alcpl,
    load_kg,
    read_source,
    section_index,
    section_starts,
)
from .prereq_gold import gold_text_terms

EXPECTED_DIRECTION = {"Prerequisite": "forward", "Extension": "backward"}


def direction(ps, pt):
    if ps is None or pt is None:
        return "unlocated"
    return "forward" if ps < pt else "backward" if ps > pt else "tie"


def forward_stats(directions, reps):
    f = sum(d == "forward" for d in directions)
    b = sum(d == "backward" for d in directions)
    out = {"forward": f, "backward": b,
           "tie": sum(d == "tie" for d in directions),
           "unlocated": sum(d == "unlocated" for d in directions)}
    n = f + b
    if n == 0:
        out.update(forward_rate=float("nan"), ci95=(float("nan"), float("nan")), p_vs_random=float("nan"))
        return out
    flags = [1] * f + [0] * b
    out["forward_rate"] = f / n
    out["ci95"] = bootstrap_ci(lambda idx: sum(flags[i] for i in idx) / len(idx), n, reps)
    out["p_vs_random"] = float(binomtest(f, n, 0.5).pvalue)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kg-dir", type=Path, default=DEFAULT_KG_DIR, help="folder with concepts.csv and relations.csv")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="textbook .txt")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: <kg-dir>/kg_eval)")
    ap.add_argument("--reps", type=int, default=2000, help="bootstrap resamples")
    args = ap.parse_args()
    out_dir = args.out or args.kg_dir / "kg_eval"
    out_dir.mkdir(parents=True, exist_ok=True)

    concepts, relations = load_kg(args.kg_dir)
    text = read_source(args.source)
    starts = section_starts(text)

    char_pos = {cid: first_position(terms, text) for cid, terms in concept_terms(concepts).items()}
    sec_pos = {cid: section_index(p, starts) for cid, p in char_pos.items()}
    names = dict(zip(concepts["concept_id"], concepts["concept_name"]))

    rel = relations.copy()
    rel["weight"] = pd.to_numeric(rel["weight"], errors="coerce")
    rel["source_name"] = rel["source_id"].map(names)
    rel["target_name"] = rel["target_id"].map(names)
    rel["source_pos"] = rel["source_id"].map(char_pos)
    rel["target_pos"] = rel["target_id"].map(char_pos)
    rel["dir_char"] = [direction(char_pos.get(s), char_pos.get(t)) for s, t in zip(rel["source_id"], rel["target_id"])]
    rel["dir_section"] = [direction(sec_pos.get(s), sec_pos.get(t)) for s, t in zip(rel["source_id"], rel["target_id"])]

    report = {
        "kg_dir": str(args.kg_dir),
        "concepts": len(concepts),
        "concepts_located_in_text": sum(p is not None for p in char_pos.values()),
        "concepts_not_located": sorted(names[c] for c, p in char_pos.items() if p is None),
        "sections_detected": len(starts),
        "by_relation_type": {},
    }
    for rt, grp in rel.groupby("relation_type"):
        report["by_relation_type"][rt] = {
            "n_edges": len(grp),
            "expected_direction": EXPECTED_DIRECTION.get(rt, "none"),
            "char": forward_stats(grp["dir_char"].tolist(), args.reps),
            "section": forward_stats(grp["dir_section"].tolist(), args.reps),
        }

    # Prerequisite graph: closure agreement, depth vs position, weight vs direction
    pre = rel[rel["relation_type"].str.strip().str.lower() == "prerequisite"]
    G = nx.DiGraph()
    G.add_edges_from(zip(pre["source_id"], pre["target_id"]))
    closure_dirs = [direction(char_pos.get(u), char_pos.get(v))
                    for u in G for v in nx.descendants(G, u)]
    report["prereq_closure_agreement"] = forward_stats(closure_dirs, args.reps)

    if nx.is_directed_acyclic_graph(G):
        depth = {}
        for n in nx.topological_sort(G):
            depth[n] = max((depth[p] + 1 for p in G.predecessors(n)), default=0)
        nodes = [n for n in G if char_pos.get(n) is not None]
        tau = kendalltau([depth[n] for n in nodes], [char_pos[n] for n in nodes], variant="b")
        report["prereq_depth_vs_position"] = {"n_nodes": len(nodes), "kendall_tau_b": float(tau.statistic),
                                              "p_value": float(tau.pvalue), "max_depth": max(depth.values(), default=0)}
    else:
        report["prereq_depth_vs_position"] = {"error": "Prerequisite graph has cycles; depth undefined"}

    dec = pre[pre["dir_char"].isin(["forward", "backward"])]
    report["prereq_weight_auc_forward"] = {
        "n": len(dec), "n_forward": int((dec["dir_char"] == "forward").sum()),
        "roc_auc": auc(dec["weight"].tolist(), (dec["dir_char"] == "forward").astype(int).tolist()),
    }

    # Reference: how often AL-CPL gold prerequisites are taught first in this book
    gold = load_alcpl()
    gpos = {g: first_position(gold_text_terms(g), text) for g in set(gold["concept"]) | set(gold["prereq"])}
    ref = {}
    for label, name in ((1, "gold_positive"), (0, "gold_negative")):
        g = gold[gold["label"] == label]
        ref[name] = {
            "char": forward_stats([direction(gpos[b], gpos[a]) for a, b in zip(g["concept"], g["prereq"])], args.reps),
            "section": forward_stats([direction(section_index(gpos[b], starts), section_index(gpos[a], starts))
                                      for a, b in zip(g["concept"], g["prereq"])], args.reps),
        }
    report["gold_reference"] = ref

    (out_dir / "book_order_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    rel[["relation_id", "source_name", "target_name", "relation_type", "weight", "source_pos", "target_pos",
         "dir_char", "dir_section"]].to_csv(out_dir / "book_order_edges.csv", index=False)

    def line(label, s):
        ci = f"[{fmt(s['ci95'][0], 2)}, {fmt(s['ci95'][1], 2)}]"
        return (f"  {label:<24}{s['forward']:>5}{s['backward']:>5}{s['tie']:>5}{s['unlocated']:>6}"
                f"{fmt(s['forward_rate']):>9}  {ci:<14}{fmt(s['p_vs_random']):>8}")

    print(f"Concepts located in text: {report['concepts_located_in_text']}/{len(concepts)}; sections: {len(starts)}")
    for gran in ("char", "section"):
        print(f"\nForward rate by relation type ({gran} level)")
        print(f"  {'':<24}{'fwd':>5}{'bwd':>5}{'tie':>5}{'unloc':>6}{'rate':>9}  {'95% CI':<14}{'p(0.5)':>8}")
        for rt, r in sorted(report["by_relation_type"].items(), key=lambda kv: -kv[1]["n_edges"]):
            mark = {"forward": "*", "backward": "^"}.get(r["expected_direction"], " ")
            print(line(f"{mark}{rt} (n={r['n_edges']})", r[gran]))
        for name, r in ref.items():
            print(line(f" AL-CPL {name}", r[gran]))
    print("  (* = should point forward, so a high rate is good; ^ = should point backward, so a LOW rate is good)")
    print("\nPrerequisite closure agreement (char):")
    print(line(" u ~> v pairs", report["prereq_closure_agreement"]))
    d = report["prereq_depth_vs_position"]
    if "kendall_tau_b" in d:
        print(f"\nKendall tau-b (prereq depth vs first mention): {fmt(d['kendall_tau_b'])} "
              f"(p={fmt(d['p_value'])}, n={d['n_nodes']}, max depth={d['max_depth']})")
    w = report["prereq_weight_auc_forward"]
    print(f"Weight AUC for 'edge points forward' (Prerequisite): {fmt(w['roc_auc'])} (n={w['n']}, forward={w['n_forward']})")
    print(f"\nWrote {out_dir / 'book_order_report.json'} and book_order_edges.csv")


if __name__ == "__main__":
    main()
