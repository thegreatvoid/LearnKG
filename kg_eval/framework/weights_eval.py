"""Phases 5 and 6: co-occurrence diagnostics and heuristic-weight comparison.

PREREQUISITE RANKING (AL-CPL labels, used for prerequisite ranking ONLY): the query/candidate protocol of
kg_eval.weight_ranking (query A, its labelled candidates B, relevance = B is a prerequisite of A). Every method scores
the same pairs. Methods are fixed formulas; nothing is fitted here (no coefficients are tuned on these labels).
Run on two concept inventories (rule_v3 and kgx_v2) as a robustness check, not as generalisation.

OTHER RELATION TYPES: no labels exist, so only descriptive diagnostics are reported (weight distribution per type,
factor correlations, association with per-edge grounding distance, agreement between schemes). These do NOT
establish correctness or educational relevance.

  python -m kg_eval.framework.weights_eval
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from educational_pipeline.relation_extractor import (AHP_FACTOR_WEIGHTS, WEIGHTING_SCHEMES, combine, pair_factors)
from ..weight_ranking import build_queries
from .common import (KG, ROOT, cluster_bootstrap_ci, out_dir, pairwise_accuracy, ranking_metrics, sign_flip_p,
                     write_json, RELATION_TYPES)

FACTORS = ["semantic_similarity", "cooccurrence", "chapter_proximity", "educational_context"]
METHODS = {
    "AHP (0.52S+0.24C+0.09P+0.15E)": lambda f: combine(f, WEIGHTING_SCHEMES["ahp"]),
    "S only": lambda f: f["semantic_similarity"],
    "C only (min(1,n/3))": lambda f: f["cooccurrence"],
    "P only": lambda f: f["chapter_proximity"],
    "E only": lambda f: f["educational_context"],
    "C+E (0.8C+0.2E)": lambda f: combine(f, WEIGHTING_SCHEMES["cooc_struct_a0.8"]),
    "raw co-occurrence count n": lambda f: f["cooccurrence_count"],
    "NPMI": lambda f: f["npmi"],
    "book order (gap)": lambda f: f["book_order"],
    "random": lambda f: 0.0,
}
BASE = "AHP (0.52S+0.24C+0.09P+0.15E)"


def evaluate_methods(queries):
    per = {}
    for name, fn in METHODS.items():
        rows = []
        for q in queries:
            sc = [fn(f) for f in q["feats"]]
            r = ranking_metrics(sc, q["rels"])
            r["pairwise_acc"] = pairwise_accuracy(sc, q["rels"])
            rows.append(r)
        per[name] = rows
    out = {}
    for name, rows in per.items():
        out[name] = {}
        for k in rows[0]:
            v = [r[k] for r in rows]
            d = [a[k] - b[k] for a, b in zip(rows, per[BASE])]
            out[name][k] = {"mean": float(np.nanmean(v)), "ci95": cluster_bootstrap_ci(v),
                            "minus_ahp": float(np.nanmean(d)), "minus_ahp_ci95": cluster_bootstrap_ci(d),
                            "p_sign_flip_vs_ahp": sign_flip_p(d) if name != BASE else None}
    return out


def cooccurrence_diagnostics(queries):
    feats = [f for q in queries for f in q["feats"]]
    freq_c = np.array([f["freq_candidate"] for f in feats], float)
    C = np.array([f["cooccurrence"] for f in feats]); n = np.array([f["cooccurrence_count"] for f in feats], float)
    E = np.array([f["educational_context"] for f in feats]); P = np.array([f["chapter_proximity"] for f in feats])
    S = np.array([f["semantic_similarity"] for f in feats]); npmi = np.array([f["npmi"] for f in feats])
    rel = np.array([r for q in queries for r in q["rels"]])
    sp = lambda a, b: float(spearmanr(a, b).statistic)
    # hub analysis: top-10% most frequent candidates among all candidates
    thr = np.quantile(freq_c, 0.9)
    hub = freq_c >= thr
    top5_hub, rel_hub = [], []
    for q in queries:
        fc = np.array([f["freq_candidate"] for f in q["feats"]]); c = np.array([f["cooccurrence"] for f in q["feats"]])
        order = np.argsort(-c, kind="stable")[:5]
        top5_hub.append(float((fc[order] >= thr).mean()))
    return {
        "definition": {"unit": "sentence (pipeline split after . ? ! within chunks)", "raw": "n = sentences mentioning both",
                       "C": "min(1, n/3): saturates at 3 sentences, no frequency normalisation",
                       "NPMI": "log(n N / (n_a n_b)) / -log(n/N); -1 if n = 0",
                       "repeated mentions": "a sentence counts once per pair however often the names repeat"},
        "pairs": len(feats), "pairs_with_n0": int((n == 0).sum()), "pairs_C_saturated": int((C >= 1).sum()),
        "spearman": {"C_vs_candidate_frequency": sp(C, freq_c), "npmi_vs_candidate_frequency": sp(npmi, freq_c),
                     "C_vs_E": sp(C, E), "C_vs_P": sp(C, P), "C_vs_S": sp(C, S), "E_vs_P": sp(E, P),
                     "relevance_vs_candidate_frequency": sp(rel, freq_c)},
        "hub_threshold_sentences": float(thr),
        "hub_share_all_candidates": float(hub.mean()), "hub_share_relevant": float(hub[rel == 1].mean()),
        "hub_share_top5_by_C_mean_over_queries": float(np.mean(top5_hub)),
        "relevance_rate_hub": float(rel[hub].mean()), "relevance_rate_nonhub": float(rel[~hub].mean()),
    }


def other_types_diagnostics(edge_checks_csv, kg: KG):
    """Descriptive only, per relation type, for the rule_v3 KG (it stores all factors and schemes per edge)."""
    r = kg.relations.copy()
    num = lambda c: pd.to_numeric(r[c], errors="coerce")
    chk = pd.read_csv(edge_checks_csv)
    r = r.merge(chk[["relation_id", "grounding_distance", "n_support_sentences"]], on="relation_id", how="left")
    out = {}
    for ty in RELATION_TYPES:
        d = r[r.relation_type == ty]
        if d.empty:
            out[ty] = {"edges": 0}
            continue
        w = pd.to_numeric(d["weight_ahp"], errors="coerce")
        res = {"edges": len(d), "weight_ahp_quartiles": [float(w.quantile(q)) for q in (0, .25, .5, .75, 1)]}
        if len(d) >= 5:
            fac = {k: pd.to_numeric(d[c], errors="coerce") for k, c in
                   [("S", "semantic_similarity"), ("C", "cooccurrence_count"), ("P", "chapter_proximity"), ("E", "educational_context")]}
            res["factor_spearman"] = {f"{a}_{b}": float(spearmanr(fac[a], fac[b]).statistic)
                                      for i, a in enumerate("SCPE") for b in "SCPE"[i + 1:]}
            res["spearman_weight_vs_grounding_distance"] = float(spearmanr(w, d.grounding_distance).statistic)
            res["spearman_weight_vs_support_sentences"] = float(spearmanr(w, d.n_support_sentences).statistic)
            res["spearman_ahp_vs_cooc_only"] = float(spearmanr(w, pd.to_numeric(d["weight_cooc_only"])).statistic)
        out[ty] = res
    return out


def symmetry_check(kg: KG):
    """w(A,B) vs w(B,A) for every edge, from the same pair-factor functions the pipeline uses."""
    idx, valid = kg.mention_index, kg.valid_definitions
    diffs = []
    for s, t in zip(kg.relations.source_id, kg.relations.target_id):
        a, b = kg.objects[s], kg.objects[t]
        diffs.append(abs(combine(pair_factors(a, b, idx, valid)) - combine(pair_factors(b, a, idx, valid))))
    return {"edges_checked": len(diffs), "max_abs_difference": float(max(diffs)) if diffs else None,
            "conclusion": "w(A,B) = w(B,A) for every edge: the weight cannot decide directed-edge correctness"
            if diffs and max(diffs) == 0 else "asymmetric for some edges"}


def main():
    res = {"note": __doc__, "prerequisite_ranking": {}, "cooccurrence": {}}
    for name, path in [("rule_v3", "data_output/baseline_v3/ck12_geometry"), ("kgx_v2", "data_output/ck12_geometry_kgx_v2")]:
        queries, skipped = build_queries(ROOT / path, ROOT / "data_input/ck12_geometry/ck12_basic_geometry_concepts.txt", False)
        res["prerequisite_ranking"][name] = {"queries": len(queries), "pairs": sum(len(q["rels"]) for q in queries),
                                             "relevant": sum(sum(q["rels"]) for q in queries), "skipped": skipped,
                                             "methods": evaluate_methods(queries)}
        res["cooccurrence"][name] = cooccurrence_diagnostics(queries)
    rv3 = KG("rule_v3")
    res["symmetry"] = symmetry_check(rv3)
    res["other_relation_types_rule_v3"] = other_types_diagnostics(
        ROOT / "data_output/eval_framework/relations/edge_checks_rule_v3.csv", rv3)
    write_json(out_dir("weights") / "weights_report.json", res)
    for name, r in res["prerequisite_ranking"].items():
        print(f"\n## {name}: queries={r['queries']} pairs={r['pairs']} relevant={r['relevant']}")
        for m, v in r["methods"].items():
            print(f"  {m:32s} NDCG@5 {v['ndcg@5']['mean']:.3f} NDCG@10 {v['ndcg@10']['mean']:.3f} P@5 {v['p@5']['mean']:.3f} "
                  f"R@10 {v['r@10']['mean']:.3f} pairAcc {v['pairwise_acc']['mean']:.3f}  dNDCG@10 vs AHP {v['ndcg@10']['minus_ahp']:+.3f} "
                  f"[{v['ndcg@10']['minus_ahp_ci95'][0]:+.3f},{v['ndcg@10']['minus_ahp_ci95'][1]:+.3f}]")
        c = res["cooccurrence"][name]
        print("  cooc:", {k: round(v, 3) for k, v in c["spearman"].items()}, "| hub share all/relevant/top5-by-C:",
              round(c["hub_share_all_candidates"], 3), round(c["hub_share_relevant"], 3), round(c["hub_share_top5_by_C_mean_over_queries"], 3))
    print("\nsymmetry:", res["symmetry"])


if __name__ == "__main__":
    main()
