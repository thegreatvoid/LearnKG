"""C. Weighting ablation with the concept/edge set frozen. Only the weight function varies.

Variants: uniform, S-only, C-only, P-only, E-only, full minus each component, full (AHP), full (tuned on dev).
Metrics (vs. blind educational-importance ratings from `weight_validity rate`):
  Spearman rho with mean rating; AUC for 'rating >= 4'. Reported on all / dev / held-out split.
Split: ck12_geometry chapters 1-6 = dev, 7-12 = held-out (single book; replace with per-book split when available).

  python -m kg_eval.weight_ablation
"""

import argparse
import itertools
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from educational_pipeline.normalizer import NormalizedConcept
from educational_pipeline.relation_extractor import (AHP_FACTOR_WEIGHTS, chapter_proximity,
                                                     educational_context_score, semantic_similarity)

from .data import (DEFAULT_KG_DIR, DEFAULT_OUT, DEFAULT_SOURCE, auc, bootstrap_ci, edge_table, fmt, load_kg,
                   norm_name, read_source, spearman, split_sentences)
from .weight_validity import load_ratings

COMPONENTS = ["semantic_similarity", "cooccurrence", "chapter_proximity", "educational_context"]
SHORT = {"semantic_similarity": "S", "cooccurrence": "C", "chapter_proximity": "P", "educational_context": "E"}
DEV_CHAPTERS = set(range(1, 7))


def to_concept(r):
    return NormalizedConcept(concept_id=r["concept_id"], concept_name=r["concept_name"], definition=r["definition"],
                             chapter=r["chapter"], section=r["section"])


def stored_component_matrix(edges):
    """Exact factors saved by the pipeline (relations.csv columns); None for older exports."""
    need = ["cooccurrence_count", "semantic_similarity", "chapter_proximity", "educational_context"]
    if not all(c in edges for c in need):
        return None
    M = pd.DataFrame({
        "semantic_similarity": pd.to_numeric(edges["semantic_similarity"]),
        "cooccurrence": (pd.to_numeric(edges["cooccurrence_count"]) / 3.0).clip(upper=1.0),
        "chapter_proximity": pd.to_numeric(edges["chapter_proximity"]),
        "educational_context": pd.to_numeric(edges["educational_context"]),
    }, index=edges.index)
    return M


def component_matrix(concepts, edges, sentences):
    cs = {r["concept_id"]: to_concept(r) for _, r in concepts.iterrows()}
    names = {cid: norm_name(c.concept_name) for cid, c in cs.items()}
    sent_norm = [norm_name(s) for s in sentences]

    def mentions(cid):
        return {i for i, s in enumerate(sent_norm) if names[cid] and re.search(rf"\b{re.escape(names[cid])}\b", s)}

    cache = {}
    rows = []
    for _, e in edges.iterrows():
        a, b = cs[e["source_id"]], cs[e["target_id"]]
        for cid in (a.concept_id, b.concept_id):
            cache.setdefault(cid, mentions(cid))
        # same normalization as the pipeline: sentence-level co-mentions, capped at 3 -> [0,1]
        cooc = min(1.0, len(cache[a.concept_id] & cache[b.concept_id]) / 3.0)
        rows.append({"semantic_similarity": semantic_similarity(a, b), "cooccurrence": cooc,
                     "chapter_proximity": chapter_proximity(a, b), "educational_context": educational_context_score(a, b)})
    return pd.DataFrame(rows, index=edges.index)


def score(M, w):
    return (M[COMPONENTS].values * np.array([w.get(c, 0.0) for c in COMPONENTS])).sum(axis=1)


def variants(tuned):
    base = AHP_FACTOR_WEIGHTS
    v = {"uniform": {c: 0.0 for c in COMPONENTS}}  # constant score; handled below
    for c in COMPONENTS:
        v[f"{SHORT[c]}-only"] = {c: 1.0}
    for c in COMPONENTS:
        rest = {k: x for k, x in base.items() if k != c}
        z = sum(rest.values())
        v[f"full minus {SHORT[c]}"] = {k: x / z for k, x in rest.items()}
    v["full (AHP)"] = dict(base)
    v["full (tuned on dev)"] = tuned
    return v


def metrics(s, y, hi):
    return {"n": len(y), "rho": spearman(list(s), list(y)), "auc_ge4": auc(list(s), list(hi))}


def tune(M, y, step=0.05):
    """Grid search on the weight simplex maximizing dev Spearman."""
    k = round(1 / step)
    best, bw = -2, None
    for combo in itertools.product(range(k + 1), repeat=3):
        if sum(combo) > k:
            continue
        w = [c / k for c in combo] + [1 - sum(combo) / k]
        sc = (M[COMPONENTS].values * np.array(w)).sum(axis=1)
        r = spearman(list(sc), list(y))
        if r == r and r > best:
            best, bw = r, w
    return dict(zip(COMPONENTS, bw)), best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg-dir", default=str(DEFAULT_KG_DIR))
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    out = Path(a.out)
    concepts, relations = load_kg(Path(a.kg_dir))
    edges = edge_table(concepts, relations)
    ratings = load_ratings(out / "judge_cache.jsonl")
    edges = edges[edges.relation_id.isin(ratings)].copy()
    if len(edges) < 20:
        raise SystemExit("Run `python -m kg_eval.weight_validity sample/rate` first (need rated edges).")
    edges["rating"] = [np.mean(list(ratings[r].values())) for r in edges.relation_id]
    edges["hi"] = (edges["rating"] >= 4).astype(int)
    edges["split"] = ["dev" if c in DEV_CHAPTERS else ("test" if pd.notna(c) else "unassigned")
                      for c in edges["edge_chapter"]]
    M = stored_component_matrix(edges)
    if M is not None:
        # Only formula-weighted edges can be ablated; extractor-supplied weights bypass the formula.
        keep = edges["weight_source"] == "ahp"
        print(f"using pipeline-stored factors; {int((~keep).sum())} extractor-weighted edges excluded")
        edges, M = edges[keep], M[keep]
    else:
        print("relations.csv has no stored factors (old export): recomputing co-occurrence from text. Re-run the pipeline.")
        M = component_matrix(concepts, edges, split_sentences(read_source(a.source)))

    stored = spearman(edges["weight"].tolist(), score(M, AHP_FACTOR_WEIGHTS).tolist())
    dev = edges["split"] == "dev"
    tuned, dev_rho = tune(M[dev], edges.loc[dev, "rating"])
    V = variants(tuned)

    report = {"split_sizes": edges["split"].value_counts().to_dict(), "tuned_weights": tuned,
              "tuned_dev_rho": dev_rho, "recomputed_vs_stored_weight_rho": stored, "variants": {}}
    full_scores = score(M, V["full (AHP)"])
    for name, w in V.items():
        s = np.zeros(len(edges)) if name == "uniform" else score(M, w)
        res = {}
        for part, mask in {"all": np.ones(len(edges), bool), "dev": dev.values,
                           "heldout": (edges["split"] == "test").values}.items():
            if mask.sum() >= 5:
                res[part] = metrics(s[mask], edges["rating"].values[mask], edges["hi"].values[mask])
        # paired bootstrap on all edges: how often does removing this component beat the full formula?
        if name.startswith("full minus") or name.endswith("-only") or name == "uniform":
            y = edges["rating"].values

            def delta(idx):
                return spearman(list(full_scores[idx]), list(y[idx])) - spearman(list(s[idx]), list(y[idx]))
            lo, hi_ = bootstrap_ci(delta, len(edges), reps=1000)
            res["full_minus_variant_rho_ci95"] = [lo, hi_]
        report["variants"][name] = res
    (out / "weight_ablation_report.json").write_text(json.dumps(report, indent=2, default=float))

    print(f"split sizes {report['split_sizes']}; recomputed-vs-stored rho={fmt(stored)}")
    print(f"tuned weights {({SHORT[k]: round(v, 2) for k, v in tuned.items()})} (dev rho {fmt(dev_rho)})\n")
    print(f"{'variant':22s} {'rho all':>8s} {'rho dev':>8s} {'rho held':>9s} {'AUC held':>9s}  full-variant rho CI95")
    for name, r in report["variants"].items():
        g = lambda p, k: fmt(r.get(p, {}).get(k))
        ci = r.get("full_minus_variant_rho_ci95")
        print(f"{name:22s} {g('all','rho'):>8s} {g('dev','rho'):>8s} {g('heldout','rho'):>9s} "
              f"{g('heldout','auc_ge4'):>9s}  {[fmt(x) for x in ci] if ci else ''}")


if __name__ == "__main__":
    main()
