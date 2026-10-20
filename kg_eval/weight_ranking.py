"""Query-ranking evaluation of the edge-weight factors (no LLM, no human annotation).

Relevance judgments: AL-CPL geometry (Liang et al. 2018), independent of the system and of the textbook.
  query     = an AL-CPL concept A that matches a KG concept
  candidates= every concept B labelled against A in AL-CPL (positive or negative), matched to a KG concept
  relevant  = B is a prerequisite of A (AL-CPL label 1)
Every variant scores exactly the same (query, candidate) pairs. Scores are pair functions computed from the textbook
and the KG concepts (educational_pipeline.relation_extractor.pair_factors), so pairs without an edge are scored too.

Variants: the frozen weighting schemes (educational_pipeline.relation_extractor.WEIGHTING_SCHEMES: ahp, cooc_only,
cooc_struct_a0.8), each factor alone, AHP without each factor (remaining coefficients renormalised), equal weights,
random, and coefficients learned by 5-fold cross-validation over queries (grid on the simplex, chosen on training
folds, NDCG reported on held-out folds). Direction-aware rows use book order (B first mentioned before A): book order
alone, and book order gating a weight, to test whether a weight adds anything beyond book order.

All factors are symmetric in A and B, so this measures relatedness ranking, not direction.

  python -m kg_eval.weight_ranking --kg-dir data_output/baseline_fixed/ck12_geometry
"""

import argparse
import itertools
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from educational_pipeline.chunker import create_structure_aware_chunks
from educational_pipeline.normalizer import NormalizedConcept
from educational_pipeline.parser import parse_document
from educational_pipeline.relation_extractor import (AHP_FACTOR_WEIGHTS, WEIGHTING_SCHEMES, MentionIndex,
                                                     definition_is_valid, pair_factors)
from educational_pipeline.structure_detector import detect_educational_structures
from evaluate_prerequisite_extraction import build_extracted_concept_index, match_gold_concept

from .data import DEFAULT_ALCPL_PAIRS, DEFAULT_ALCPL_PREQS, DEFAULT_SOURCE, first_position, load_alcpl, read_source

FACTORS = ["semantic_similarity", "cooccurrence", "chapter_proximity", "educational_context"]
SHORT = {"semantic_similarity": "S", "cooccurrence": "C", "chapter_proximity": "P", "educational_context": "E"}


def ndcg_at(rels, k):
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rels[:k]))
    ideal = sorted(rels, reverse=True)
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal[:k]))
    return dcg / idcg if idcg else float("nan")


def query_ndcg(scores, rels, k, rng, ties=20):
    """NDCG@k averaged over random tie-breaks (constant scores give the random-ranking value, not a lucky order)."""
    vals = []
    idx = list(range(len(scores)))
    for _ in range(ties):
        rng.shuffle(idx)
        order = sorted(idx, key=lambda i: -scores[i])
        vals.append(ndcg_at([rels[i] for i in order], k))
    return float(np.mean(vals))


def evaluate(queries, score_fn, k, seed=0):
    rng = random.Random(seed)
    return [query_ndcg([score_fn(f) for f in q["feats"]], q["rels"], k, rng) for q in queries]


def boot_ci(vals, reps=2000, seed=0):
    rng = np.random.default_rng(seed)
    v = np.array(vals)
    means = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(reps)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_flip_p(diffs, reps=20000, seed=0):
    """Two-sided paired randomisation test (sign flips of per-query differences) for mean difference = 0."""
    d = np.array(diffs)
    if not d.any():
        return 1.0
    rng = np.random.default_rng(seed)
    obs = abs(d.mean())
    flips = rng.choice([-1.0, 1.0], size=(reps, len(d)))
    return float((np.abs((flips * d).mean(axis=1)) >= obs - 1e-12).mean())


def weighted(w):
    return lambda f: sum(w[k] * f[k] for k in w)


def build_queries(kg_dir: Path, source: Path, embeddings: bool, pairs: Path = DEFAULT_ALCPL_PAIRS,
                  preqs: Path = DEFAULT_ALCPL_PREQS):
    concepts_df = pd.read_csv(kg_dir / "concepts.csv", dtype=str, keep_default_na=False)
    concepts = {r.concept_id: NormalizedConcept(r.concept_id, r.concept_name,
                                                aliases={a.strip() for a in r.aliases.split(",") if a.strip()},
                                                definition=r.definition, chapter=r.chapter, section=r.section)
                for r in concepts_df.itertuples()}
    blocks = [b for b in parse_document(source)]
    chunks = create_structure_aware_chunks(detect_educational_structures(blocks))
    index = MentionIndex(concepts.values(), chunks)
    n_sent = sum(len([x for x in __import__("re").split(r"(?<=[.?!])\s+", ch.text)]) for ch in chunks)
    valid = {cid: definition_is_valid(c) for cid, c in concepts.items()}
    emb = None
    if embeddings:
        from sentence_transformers import SentenceTransformer  # explicit dependency
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        ids = list(concepts)
        vecs = model.encode([concepts[i].definition if valid[i] else concepts[i].concept_name for i in ids],
                            normalize_embeddings=True)
        emb = dict(zip(ids, vecs))
    text = read_source(source)
    pos = {cid: first_position([c.concept_name, *c.aliases], text) for cid, c in concepts.items()}

    gold = load_alcpl(pairs, preqs)
    by_id, term_to_cid, normalizer = build_extracted_concept_index(concepts_df)
    names = sorted(set(gold["concept"]) | set(gold["prereq"]))
    match = {g: match_gold_concept(g, term_to_cid, by_id, normalizer)[0] for g in names}

    queries, skipped = [], {"unmatched_query": 0, "no_relevant": 0, "too_few_candidates": 0}
    for a, grp in gold.groupby("concept"):
        ca = match.get(a)
        if not ca:
            skipped["unmatched_query"] += 1
            continue
        cand = {}
        for b, lab in zip(grp["prereq"], grp["label"]):
            cb = match.get(b)
            if cb and cb != ca:
                cand[cb] = max(cand.get(cb, 0), int(lab))  # two gold names may map to one KG concept
        if len(cand) < 2:
            skipped["too_few_candidates"] += 1
            continue
        if not any(cand.values()):
            skipped["no_relevant"] += 1
            continue
        feats, rels = [], []
        for cb, lab in cand.items():
            f = pair_factors(concepts[ca], concepts[cb], index, valid)
            # frequency features (exploratory, used by kg_eval.framework): sentence counts and normalised PMI
            na, nb = len(index.sentences.get(ca, ())), len(index.sentences.get(cb, ()))
            nab = f["cooccurrence_count"]
            f["freq_query"], f["freq_candidate"] = na, nb
            f["npmi"] = (math.log(nab * n_sent / (na * nb)) / -math.log(nab / n_sent)) if nab and nab < n_sent else (1.0 if nab else -1.0)
            f["s_embedding"] = max(0.0, float(emb[ca] @ emb[cb])) if emb is not None else float("nan")
            f["book_order"] = ((pos[ca] - pos[cb]) / len(text)) if pos[ca] is not None and pos[cb] is not None else 0.0
            feats.append(f)
            rels.append(lab)
        queries.append({"query": a, "feats": feats, "rels": rels, "candidates": list(cand)})
    return queries, skipped


def simplex_grid(step=0.1):
    n = round(1 / step)
    for combo in itertools.product(range(n + 1), repeat=3):
        if sum(combo) <= n:
            yield dict(zip(FACTORS, [c / n for c in combo] + [(n - sum(combo)) / n]))


def cv_tuned(queries, k, folds=5, seed=0):
    rng = random.Random(seed)
    order = list(range(len(queries)))
    rng.shuffle(order)
    held = [None] * len(queries)
    chosen = []
    grid = list(simplex_grid())
    for f in range(folds):
        test = set(order[f::folds])
        train = [queries[i] for i in order if i not in test]
        best = max(grid, key=lambda w: np.nanmean(evaluate(train, weighted(w), k)))
        chosen.append(best)
        for i in test:
            held[i] = evaluate([queries[i]], weighted(best), k)[0]
    return held, chosen


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kg-dir", type=Path, required=True)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-embeddings", action="store_true")
    ap.add_argument("--pairs", type=Path, default=DEFAULT_ALCPL_PAIRS, help="AL-CPL <subject>.pairs")
    ap.add_argument("--preqs", type=Path, default=DEFAULT_ALCPL_PREQS, help="AL-CPL <subject>.preqs")
    a = ap.parse_args()
    out = a.out or a.kg_dir / "kg_eval"
    out.mkdir(parents=True, exist_ok=True)

    queries, skipped = build_queries(a.kg_dir, a.source, not a.no_embeddings, a.pairs, a.preqs)
    n_pairs = sum(len(q["rels"]) for q in queries)
    n_rel = sum(sum(q["rels"]) for q in queries)

    ahp = dict(AHP_FACTOR_WEIGHTS)
    fwd = lambda x: 1.0 if x["book_order"] > 0 else 0.0  # candidate B is first mentioned before query A
    variants = {}
    for name, w in WEIGHTING_SCHEMES.items():  # A, B, C: the frozen schemes, same code path as the pipeline
        variants[f"scheme {name}"] = weighted(w)
    for f in FACTORS:
        variants[f"{SHORT[f]} only"] = (lambda f: (lambda x: x[f]))(f)
    variants["S only, raw (unvalidated definitions)"] = lambda x: x["s_jaccard_raw"]
    variants["S only, embedding cosine"] = lambda x: x["s_embedding"]
    variants["E only, legacy constants"] = lambda x: x["educational_context_legacy"]
    for f in FACTORS:
        rest = {k: v for k, v in ahp.items() if k != f}
        z = sum(rest.values())
        variants[f"AHP without {SHORT[f]}"] = weighted({k: v / z for k, v in rest.items()})
    variants["equal weights (0.25 each)"] = weighted({f: 0.25 for f in FACTORS})
    variants["random (constant score)"] = lambda x: 0.0
    # Direction-aware rows: book order decides direction; does a weight add anything inside the forward set?
    variants["book order (gap)"] = lambda x: x["book_order"]
    variants["book order gate x C"] = lambda x: fwd(x) * (1e-6 + x["cooccurrence"])
    variants["book order gate x scheme cooc_struct_a0.8"] = lambda x: fwd(x) * (1e-6 + weighted(WEIGHTING_SCHEMES["cooc_struct_a0.8"])(x))
    variants["book order gate x scheme ahp"] = lambda x: fwd(x) * (1e-6 + weighted(ahp)(x))
    variants["book order gate only (forward, unranked)"] = lambda x: fwd(x)

    BASE = "scheme ahp"
    # Pre-specified paired comparisons (reported with a sign-flip randomisation test, no multiplicity correction).
    COMPARISONS = [("scheme cooc_only", "scheme ahp"), ("scheme cooc_struct_a0.8", "scheme ahp"),
                   ("scheme cooc_struct_a0.8", "scheme cooc_only"), ("scheme ahp", "random (constant score)"),
                   ("scheme cooc_only", "random (constant score)"),
                   ("book order gate x C", "book order (gap)"), ("book order gate x C", "book order gate only (forward, unranked)")]

    res, per_query = {}, {}
    for name, fn in variants.items():
        per_query[name] = {k: evaluate(queries, fn, k) for k in (5, 10)}
    for name in variants:
        r = {}
        for k in (5, 10):
            vals = per_query[name][k]
            lo, hi = boot_ci(vals)
            d = np.array(vals) - np.array(per_query[BASE][k])
            r[f"ndcg@{k}"] = {"mean": float(np.mean(vals)), "ci95": [lo, hi], "minus_ahp": float(d.mean()),
                             "minus_ahp_ci95": list(boot_ci(d.tolist()))}
        res[name] = r
    tuned = {}
    for k in (5, 10):
        held, chosen = cv_tuned(queries, k)
        lo, hi = boot_ci(held)
        d = np.array(held) - np.array(per_query[BASE][k])
        tuned[f"ndcg@{k}"] = {"mean": float(np.mean(held)), "ci95": [lo, hi], "minus_ahp": float(d.mean()),
                              "minus_ahp_ci95": list(boot_ci(d.tolist())),
                              "fold_coefficients": [{SHORT[f]: round(w[f], 2) for f in FACTORS} for w in chosen]}
    res["D: learned coefficients, 5-fold CV over queries (held-out)"] = tuned
    comparisons = []
    for x, y in COMPARISONS:
        for k in (5, 10):
            d = (np.array(per_query[x][k]) - np.array(per_query[y][k])).tolist()
            comparisons.append({"a": x, "b": y, "k": k, "mean_diff": float(np.mean(d)), "ci95": list(boot_ci(d)),
                                "p_sign_flip": sign_flip_p(d)})

    allf = [f for q in queries for f in q["feats"]]
    P = [f["chapter_proximity"] for f in allf]
    redundancy = {
        "spearman_P_vs_E": float(spearmanr(P, [f["educational_context"] for f in allf]).statistic),
        "spearman_P_vs_E_legacy": float(spearmanr(P, [f["educational_context_legacy"] for f in allf]).statistic),
        "spearman_C_vs_E": float(spearmanr([f["cooccurrence"] for f in allf], [f["educational_context"] for f in allf]).statistic),
        "spearman_S_jaccard_vs_S_embedding": float(spearmanr([f["semantic_similarity"] for f in allf], [f["s_embedding"] for f in allf]).statistic),
    }
    report = {"kg_dir": str(a.kg_dir), "gold": "AL-CPL geometry", "queries": len(queries), "pairs": n_pairs,
              "relevant_pairs": n_rel, "skipped_queries": skipped, "results": res, "comparisons": comparisons,
              "factor_redundancy": redundancy, "schemes": WEIGHTING_SCHEMES,
              "notes": ["Factors are symmetric; this tests relatedness ranking, not prerequisite direction.",
                        "CIs: bootstrap over queries (2000 resamples). minus_ahp is a paired per-query difference.",
                        "AHP coefficients are fixed expert judgements; only the CV-tuned row is fitted, on training folds."]}
    (out / "weight_ranking_report.json").write_text(json.dumps(report, indent=2))

    print(f"queries={len(queries)} pairs={n_pairs} relevant={n_rel} skipped={skipped}")
    print(f"{'variant':40s} {'NDCG@5 [95% CI]':>24s} {'vs AHP':>18s} {'NDCG@10 [95% CI]':>24s} {'vs AHP':>18s}")
    for name, r in res.items():
        cells = []
        for k in (5, 10):
            m = r[f"ndcg@{k}"]
            cells.append(f"{m['mean']:.3f} [{m['ci95'][0]:.3f},{m['ci95'][1]:.3f}]")
            cells.append(f"{m['minus_ahp']:+.3f} [{m['minus_ahp_ci95'][0]:+.2f},{m['minus_ahp_ci95'][1]:+.2f}]")
        print(f"{name:40s} {cells[0]:>24s} {cells[1]:>18s} {cells[2]:>24s} {cells[3]:>18s}")
    print("fold coefficients @10:", tuned["ndcg@10"]["fold_coefficients"])
    print("\npre-specified paired comparisons (a - b):")
    for c in comparisons:
        print(f"  @{c['k']:<2d} {c['a']:44s} - {c['b']:42s} {c['mean_diff']:+.3f} [{c['ci95'][0]:+.3f},{c['ci95'][1]:+.3f}]  p={c['p_sign_flip']:.4f}")
    print("redundancy:", {k: round(v, 3) for k, v in redundancy.items()})


if __name__ == "__main__":
    main()
