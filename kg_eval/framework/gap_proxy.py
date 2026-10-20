"""Phase 8: CONCEPT-LEVEL knowledge-gap proxy (not question-level gap detection, not learner modelling).

Task: for a target concept A (an AL-CPL concept matched to the KG), rank ALL other KG concepts as candidate
missing prerequisites. Relevant = AL-CPL positives of A ("direct"), or of A's transitive AL-CPL prerequisite closure
("closure"), matched to KG concepts. Candidates AL-CPL labels negative for A are judged non-relevant; every other
candidate is UNKNOWN (AL-CPL never labelled it), so two views are reported:
  judged_only  unknown candidates removed (precision over judged candidates)
  lower_bound  unknown candidates kept and counted as non-relevant (a lower bound on precision)
Methods:
  kg_graph     ancestors of A in the KG's Prerequisite graph, score 1/path length (the intended use of the KG)
  book_order   candidates first mentioned before A, score = position gap
  ahp / c_only pair-weight formulas (symmetric relatedness; they cannot say which side is the prerequisite)
  random
Learning-path validity (kg_graph and book_order only): the method's top-10 ordered prerequisite-first (topological
order of the KG graph / first mention); share of AL-CPL-labelled ordered pairs inside the path that respect the
label (x before y when x is a prerequisite of y). Book-order KGs (kgx_v2_hybrid) make book-order agreement circular.

  python -m kg_eval.framework.gap_proxy
"""

import networkx as nx
import numpy as np

from educational_pipeline.relation_extractor import WEIGHTING_SCHEMES, combine, pair_factors
from .common import KG, KGS, cluster_bootstrap_ci, gold, out_dir, ranking_metrics, write_json

KS = (5, 10)


def main():
    g = gold()
    pos = g[g.label == 1]
    neg = g[g.label == 0]
    alcpl = nx.DiGraph(list(zip(pos.prereq, pos.concept)))  # prereq -> concept
    res = {"note": __doc__, "kgs": {}}
    for name in KGS:
        kg = KG(name)
        m = {k: v["cid"] for k, v in kg.gold_matches(g).items()}
        cids = list(kg.objects)
        pre = kg.relations[kg.relations.relation_type == "Prerequisite"]
        G = nx.DiGraph(list(zip(pre.source_id, pre.target_id)))
        positions = kg.positions
        idx, valid = kg.mention_index, kg.valid_definitions
        order_index = {}
        try:
            for i, c in enumerate(nx.topological_sort(G)):
                order_index[c] = i
        except nx.NetworkXUnfeasible:
            pass
        targets = sorted(a for a in set(pos.concept) if m.get(a))
        per = {view: {meth: [] for meth in ("kg_graph", "book_order", "ahp", "c_only", "random")}
               for view in ("direct_judged_only", "direct_lower_bound", "closure_lower_bound")}
        path_valid = {"kg_graph": [0, 0], "book_order": [0, 0]}
        used = 0
        for A in targets:
            ca = m[A]
            direct = {m[b] for b in pos[pos.concept == A].prereq if m.get(b)} - {ca}
            closure = {m[b] for b in nx.ancestors(alcpl, A) if m.get(b)} - {ca}
            judged_neg = {m[b] for b in neg[neg.concept == A].prereq if m.get(b)} - direct - {ca}
            if not direct:
                continue
            used += 1
            cands = [c for c in cids if c != ca]
            dist = nx.single_source_shortest_path_length(G.reverse(copy=False), ca) if ca in G else {}
            fa = kg.objects[ca]
            sc = {
                "kg_graph": [1.0 / dist[c] if c in dist and dist[c] > 0 else 0.0 for c in cands],
                "book_order": [((positions[ca] - positions[c]) if positions.get(ca) is not None and positions.get(c) is not None
                                and positions[c] < positions[ca] else 0.0) for c in cands],
            }
            facs = [pair_factors(fa, kg.objects[c], idx, valid) for c in cands]
            sc["ahp"] = [combine(f, WEIGHTING_SCHEMES["ahp"]) for f in facs]
            sc["c_only"] = [f["cooccurrence"] for f in facs]
            sc["random"] = [0.0] * len(cands)
            for meth, s in sc.items():
                judged = [i for i, c in enumerate(cands) if c in direct or c in judged_neg]
                per["direct_judged_only"][meth].append(ranking_metrics([s[i] for i in judged], [int(cands[i] in direct) for i in judged], KS))
                per["direct_lower_bound"][meth].append(ranking_metrics(s, [int(c in direct) for c in cands], KS))
                per["closure_lower_bound"][meth].append(ranking_metrics(s, [int(c in closure) for c in cands], KS))
            for meth in ("kg_graph", "book_order"):
                top = [cands[i] for i in np.argsort(-np.array(sc[meth]), kind="stable")[:10] if sc[meth][i] > 0]
                key = (lambda c: order_index.get(c, 10**9)) if meth == "kg_graph" else (lambda c: positions.get(c) or 10**9)
                path = sorted(top, key=key)
                for i in range(len(path)):
                    for j in range(i + 1, len(path)):
                        x, y = path[i], path[j]
                        lab_xy = any(m.get(b) == x and m.get(a) == y for a, b in zip(pos.concept, pos.prereq))
                        lab_yx = any(m.get(b) == y and m.get(a) == x for a, b in zip(pos.concept, pos.prereq))
                        if lab_xy or lab_yx:
                            path_valid[meth][1] += 1
                            path_valid[meth][0] += int(lab_xy)
        out = {"targets_with_matched_prerequisites": used, "candidates_per_target": len(cids) - 1,
               "prerequisite_edges": len(pre), "uses_book_order": kg.uses_book_order}
        for view, d in per.items():
            out[view] = {}
            for meth, rows in d.items():
                out[view][meth] = {k: {"mean": float(np.nanmean([r[k] for r in rows])),
                                       "ci95": cluster_bootstrap_ci([r[k] for r in rows])} for k in rows[0]}
        out["learning_path_validity"] = {meth: {"labelled_ordered_pairs": n, "respecting": k,
                                                "share": k / n if n else None} for meth, (k, n) in path_valid.items()}
        res["kgs"][name] = out
        print(f"\n## {name}  targets={used}  candidates/target={len(cids) - 1}" + ("  [book order CIRCULAR]" if kg.uses_book_order else ""))
        for view in per:
            print("  " + view + ": " + "  ".join(f"{meth} P@5 {out[view][meth]['p@5']['mean']:.3f} R@10 {out[view][meth]['r@10']['mean']:.3f} "
                                                 f"NDCG@10 {out[view][meth]['ndcg@10']['mean']:.3f}" for meth in per[view]))
        print("  path validity:", out["learning_path_validity"])
    write_json(out_dir("gap_proxy") / "gap_proxy_report.json", res)


if __name__ == "__main__":
    main()
