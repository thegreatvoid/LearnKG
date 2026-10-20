"""Phase 7: BIGS by KG and relation type (textual grounding / coverage only).

BIGS-> (coverage): mean over book sentences of the distance to the closest verbalised triple.
BIGS<- (grounding): mean over triples of the distance to the closest book sentence. Lower is better for both.
Same corpus (kg_eval.data.split_sentences), embedder (all-MiniLM-L6-v2) and verbalisation ("s type t") everywhere.
Size control: BIGS-> falls as triples are added, so each (KG, type) with >= M triples is also scored on random
subsets of M triples (50 draws). Types with fewer than M triples get full-size values only.
BIGS does not measure correctness, direction (A type B and B type A score almost alike) or relation semantics.

  python -m kg_eval.framework.bigs_by_relation
"""

import numpy as np

from ..bigs import load_embedder
from ..data import DEFAULT_SOURCE, read_source, split_sentences
from .common import KG, KGS, RELATION_TYPES, out_dir, write_json

M = 10
DRAWS = 50


def scores(dist):
    fwd, bwd = float(dist.min(axis=1).mean()), float(dist.min(axis=0).mean())
    a, b = 1 - fwd, 1 - bwd
    return {"bigs_to_graph": fwd, "bigs_from_graph": bwd, "sym_bigs": float(1 - 2 * a * b / (a + b)) if a + b else 1.0}


def main():
    model = load_embedder()
    sents = split_sentences(read_source(DEFAULT_SOURCE))
    D = model.encode(sents, normalize_embeddings=True)
    rng = np.random.default_rng(0)
    res = {"corpus_sentences": len(sents), "embedder": "sentence-transformers/all-MiniLM-L6-v2", "subset_size": M,
           "draws": DRAWS, "kgs": {}}
    for name in KGS:
        kg = KG(name)
        rel = kg.relations
        out = {}
        for ty in RELATION_TYPES + ["ALL"]:
            d = rel if ty == "ALL" else rel[rel.relation_type == ty]
            if d.empty:
                out[ty] = {"triples": 0}
                continue
            texts = [f"{kg.name_of[s]} {t} {kg.name_of[o]}" for s, t, o in zip(d.source_id, d.relation_type, d.target_id)]
            V = model.encode(texts, normalize_embeddings=True)
            dist = 1.0 - D @ V.T
            r = {"triples": len(texts), "full": scores(dist)}
            if len(texts) >= M:
                sub = [scores(dist[:, rng.choice(len(texts), M, replace=False)]) for _ in range(DRAWS)]
                r[f"subset_{M}"] = {k: float(np.mean([x[k] for x in sub])) for k in sub[0]}
                r[f"subset_{M}_sd"] = {k: float(np.std([x[k] for x in sub])) for k in sub[0]}
            near = (dist.argmin(axis=0))
            r["evidence_examples"] = [{"triple": texts[i], "nearest_sentence": sents[near[i]],
                                       "distance": float(dist[near[i], i])} for i in range(min(2, len(texts)))]
            out[ty] = r
        res["kgs"][name] = out
        print(f"\n## {name}")
        for ty, r in out.items():
            if r["triples"]:
                s = r.get(f"subset_{M}")
                print(f"  {ty:12s} n={r['triples']:4d} full fwd/bwd {r['full']['bigs_to_graph']:.3f}/{r['full']['bigs_from_graph']:.3f}"
                      + (f"   size-{M} fwd/bwd {s['bigs_to_graph']:.3f}/{s['bigs_from_graph']:.3f}" if s else "   (n < M: no size-matched value)"))
    write_json(out_dir("bigs") / "bigs_by_relation.json", res)


if __name__ == "__main__":
    main()
