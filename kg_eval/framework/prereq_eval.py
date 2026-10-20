"""Phase 3: prerequisite evaluation of every KG against AL-CPL (independent labels).

Protocol (identical for every KG and baseline):
  - gold: AL-CPL geometry labelled pairs "is B a prerequisite of A" (label 1/0, both annotated by AL-CPL).
  - coverage: a pair is COVERED for a KG if both names match distinct KG concepts. Uncovered pairs are reported as
    coverage loss, never as negatives. Primary set = pairs covered by EVERY KG (same pairs for all methods);
    per-KG covered sets are reported too.
  - predicted edge: Prerequisite edge B -> A in relations.csv. Closure: B reaches A via Prerequisite edges.
  - continuous score: pair_scores score_Prerequisite(B->A) if the KG has one, else the edge weight (0 if no edge).
  - KG Prerequisite edges between concepts that AL-CPL never labelled are counted as UNKNOWN, not false positives.
  - ranking: per query A, its labelled covered candidates B. NDCG/P/R@5,10 averaged over 20 random tie-breaks.
  - CIs: bootstrap over queries (clusters), 2000 resamples; Wilson CI for direction accuracy.
  - baselines on the same pairs: book order (B first mentioned before A; score = position gap), random.
  Book-order agreement of a KG built with book order (kgx_v2_hybrid) is circular and flagged.

  python -m kg_eval.framework.prereq_eval
"""

import networkx as nx
import numpy as np
import pandas as pd

from .common import (KG, KGS, cluster_bootstrap_ci, gold, out_dir, prf, ranking_metrics, roc_auc, wilson,
                     write_json)


def kg_scores(kg: KG):
    pre = kg.relations[kg.relations.relation_type == "Prerequisite"]
    edges = {(s, t): w for s, t, w in zip(pre.source_id, pre.target_id, pre.weight_f)}
    G = nx.DiGraph(list(edges))
    if kg.pair_scores is not None:
        cont = {(s, t): float(v) for s, t, v in zip(kg.pair_scores.source_id, kg.pair_scores.target_id,
                                                     kg.pair_scores.score_Prerequisite)}
        cont_name = "pair_scores.score_Prerequisite"
    else:
        cont, cont_name = edges, "edge weight"
    return edges, G, cont, cont_name


def pair_table(kg: KG, g: pd.DataFrame):
    m = kg.gold_matches(g)
    edges, G, cont, cont_name = kg_scores(kg)
    pos = kg.positions
    rows = []
    for a, b, y in zip(g.concept, g.prereq, g.label):
        ca, cb = m[a]["cid"], m[b]["cid"]
        covered = bool(ca and cb and ca != cb)
        r = {"concept": a, "prereq": b, "label": int(y), "covered": covered}
        if covered:
            r["edge"] = int((cb, ca) in edges)
            r["edge_reversed"] = int((ca, cb) in edges)
            r["closure"] = int(cb in G and ca in G and nx.has_path(G, cb, ca))
            r["score"] = float(cont.get((cb, ca), 0.0))
            pa, pb = pos.get(ca), pos.get(cb)
            r["book_order_score"] = (pa - pb) if pa is not None and pb is not None else 0.0
            r["book_order_pred"] = int(pa is not None and pb is not None and pb < pa)
        rows.append(r)
    labelled = {(m[b]["cid"], m[a]["cid"]) for a, b in zip(g.concept, g.prereq) if m[a]["cid"] and m[b]["cid"]}
    unknown_edges = sum(1 for e in edges if e not in labelled)
    return pd.DataFrame(rows), unknown_edges, cont_name, len(edges)


def classification(df, col, reps=2000):
    def counts(d):
        return int(((d[col] == 1) & (d.label == 1)).sum()), int(((d[col] == 1) & (d.label == 0)).sum()), \
               int(((d[col] == 0) & (d.label == 1)).sum())
    base = prf(*counts(df))
    groups = [d for _, d in df.groupby("concept")]
    rng = np.random.default_rng(0)
    f1s, ps, rs = [], [], []
    for _ in range(reps):
        s = pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        x = prf(*counts(s))
        f1s.append(x["f1"]); ps.append(x["precision"]); rs.append(x["recall"])
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
    return {**base, "precision_ci95": ci(ps), "recall_ci95": ci(rs), "f1_ci95": ci(f1s)}


def auc_with_ci(df, col, reps=2000):
    groups = [d for _, d in df.groupby("concept")]
    rng = np.random.default_rng(0)
    vals = []
    for _ in range(reps):
        s = pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        vals.append(roc_auc(s[col], s.label))
    return {"auc": roc_auc(df[col], df.label), "auc_ci95": [float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))]}


def ranking(df, col):
    per_q = []
    for a, d in df.groupby("concept"):
        if d.label.sum() == 0 or len(d) < 2:
            continue
        per_q.append(ranking_metrics(d[col].tolist() if col else [0.0] * len(d), d.label.tolist()))
    out = {"queries": len(per_q)}
    for k in per_q[0]:
        v = [q[k] for q in per_q]
        out[k] = float(np.nanmean(v))
        out[k + "_ci95"] = cluster_bootstrap_ci(v)
    return out


def direction(df):
    p = df[df.label == 1]
    kg_dec = p[(p.edge + p.edge_reversed) == 1]
    bo_dec = p[p.book_order_score != 0]
    return {"kg_edges": {"decided": len(kg_dec), "correct": int(kg_dec.edge.sum()),
                         "accuracy": kg_dec.edge.mean() if len(kg_dec) else float("nan"),
                         "wilson95": wilson(int(kg_dec.edge.sum()), len(kg_dec))},
            "book_order": {"decided": len(bo_dec), "correct": int((bo_dec.book_order_score > 0).sum()),
                           "accuracy": float((bo_dec.book_order_score > 0).mean()),
                           "wilson95": wilson(int((bo_dec.book_order_score > 0).sum()), len(bo_dec))}}


def evaluate_set(df):
    pos_rate = df.label.mean()
    return {
        "pairs": len(df), "positives": int(df.label.sum()), "prevalence": float(pos_rate),
        "kg_edge": classification(df, "edge"), "kg_closure": classification(df, "closure"),
        "book_order": classification(df, "book_order_pred"),
        "random_expected": {"precision": float(pos_rate), "recall": 0.5,
                            "f1": float(2 * pos_rate * 0.5 / (pos_rate + 0.5)),
                            "note": "analytic: predict positive with probability 0.5"},
        "auc_kg_score": auc_with_ci(df, "score"), "auc_book_order": auc_with_ci(df, "book_order_score"),
        "ranking_kg_score": ranking(df, "score"), "ranking_book_order": ranking(df, "book_order_score"),
        "ranking_random": ranking(df, None),
        "direction": direction(df),
    }


def main():
    g = gold()
    tables, meta = {}, {}
    for name in KGS:
        kg = KG(name)
        t, unknown, cont_name, n_edges = pair_table(kg, g)
        tables[name] = t
        meta[name] = {"desc": kg.desc, "uses_book_order": kg.uses_book_order, "continuous_score": cont_name,
                      "prerequisite_edges": n_edges, "prerequisite_edges_unlabelled_in_alcpl": unknown,
                      "covered_pairs": int(t.covered.sum()), "uncovered_pairs": int((~t.covered).sum()),
                      "uncovered_positives": int(((~t.covered) & (t.label == 1)).sum())}
    key = ["concept", "prereq"]
    common = None
    for t in tables.values():
        c = set(map(tuple, t[t.covered][key].values))
        common = c if common is None else common & c
    res = {"protocol": __doc__, "gold": {"pairs": len(g), "positives": int(g.label.sum())}, "kgs": {}}
    for name, t in tables.items():
        cov = t[t.covered].copy()
        com = cov[cov[key].apply(tuple, axis=1).isin(common)]
        res["kgs"][name] = {**meta[name], "common_set": evaluate_set(com), "own_covered_set": evaluate_set(cov),
                            "end_to_end_recall_all_positives": {
                                "edge": int(cov[(cov.label == 1)].edge.sum()) / int(g.label.sum()),
                                "closure": int(cov[(cov.label == 1)].closure.sum()) / int(g.label.sum())}}
        t.to_csv(out_dir("prerequisite") / f"pairs_{name}.csv", index=False)
    res["common_set_pairs"] = len(common)
    write_json(out_dir("prerequisite") / "prerequisite_report.json", res)

    print(f"common covered pairs: {len(common)}")
    fmt = lambda x: "nan" if x != x else f"{x:.3f}"
    for name, r in res["kgs"].items():
        c = r["common_set"]
        e, cl, rk = c["kg_edge"], c["kg_closure"], c["ranking_kg_score"]
        print(f"{name:15s} edge P/R/F1 {fmt(e['precision'])}/{fmt(e['recall'])}/{fmt(e['f1'])}  closure F1 {fmt(cl['f1'])} "
              f"[{fmt(cl['f1_ci95'][0])},{fmt(cl['f1_ci95'][1])}]  AUC {fmt(c['auc_kg_score']['auc'])}  "
              f"NDCG@10 {fmt(rk['ndcg@10'])}  P@5 {fmt(rk['p@5'])}  R@10 {fmt(rk['r@10'])}  "
              f"dir {c['direction']['kg_edges']['correct']}/{c['direction']['kg_edges']['decided']}"
              + ("  [CIRCULAR vs book order]" if r["uses_book_order"] else ""))
    c = res["kgs"]["rule_v3"]["common_set"]
    print(f"{'book order':15s} P/R/F1 {fmt(c['book_order']['precision'])}/{fmt(c['book_order']['recall'])}/{fmt(c['book_order']['f1'])} "
          f"AUC {fmt(c['auc_book_order']['auc'])}  NDCG@10 {fmt(c['ranking_book_order']['ndcg@10'])}  "
          f"dir {c['direction']['book_order']['correct']}/{c['direction']['book_order']['decided']}")
    print(f"{'random':15s} NDCG@10 {fmt(c['ranking_random']['ndcg@10'])}  expected F1 {fmt(c['random_expected']['f1'])}")


if __name__ == "__main__":
    main()
