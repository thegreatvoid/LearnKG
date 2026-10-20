"""BIGS for several KGs of the same book, with graph size controlled.

Same corpus (textbook sentences, kg_eval.data.split_sentences), same embedder, same verbalisation
("subject relation_type object") for every KG. BIGS-> (coverage) falls as a graph adds triples even if they are
unrelated, so besides the full-size value each KG is also scored on random subsets of m triples, m = the smallest
graph's size (mean and SD over --draws subsets). BIGS says nothing about prerequisite direction or correctness:
report it next to kg_eval.prereq_gold.

  python -m kg_eval.bigs_compare --kg-dirs data_output/baseline_fixed/ck12_geometry data_output/ck12_geometry_kgx_v2 ...
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .bigs import DEFAULT_EMBEDDER, load_embedder, verbalize_triple
from .data import DEFAULT_SOURCE, read_source, split_sentences


def triples(kg_dir: Path):
    c = pd.read_csv(kg_dir / "concepts.csv", dtype=str, keep_default_na=False).set_index("concept_id").concept_name
    r = pd.read_csv(kg_dir / "relations.csv", dtype=str, keep_default_na=False)
    return [verbalize_triple(c[s], t, c[o]) for s, t, o in zip(r.source_id, r.relation_type, r.target_id)
            if s in c.index and o in c.index]


def scores(dist):
    fwd, bwd = float(dist.min(axis=1).mean()), float(dist.min(axis=0).mean())
    a, b = 1 - fwd, 1 - bwd
    return fwd, bwd, float(1 - 2 * a * b / (a + b)) if a + b else 1.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kg-dirs", type=Path, nargs="+", required=True)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--embedder", default=DEFAULT_EMBEDDER)
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--out", type=Path, default=Path("data_output/bigs_compare.json"))
    a = ap.parse_args()
    model = load_embedder(a.embedder)
    sents = split_sentences(read_source(a.source))
    D = model.encode(sents, normalize_embeddings=True)
    T = {d: triples(d) for d in a.kg_dirs}
    m = min(len(t) for t in T.values())
    rng = np.random.default_rng(0)
    rows = []
    for d, ts in T.items():
        V = model.encode(ts, normalize_embeddings=True)
        dist = 1.0 - D @ V.T
        full = scores(dist)
        sub = np.array([scores(dist[:, rng.choice(len(ts), m, replace=False)]) for _ in range(a.draws)])
        rows.append({"kg": str(d), "n_triples": len(ts), "full": dict(zip(["fwd", "bwd", "sym"], full)),
                     f"subsample_m{m}_mean": dict(zip(["fwd", "bwd", "sym"], sub.mean(0).tolist())),
                     f"subsample_m{m}_sd": dict(zip(["fwd", "bwd", "sym"], sub.std(0).tolist()))})
    out = {"corpus": str(a.source), "doc_units": len(sents), "embedder": a.embedder, "verbalisation":
           "subject relation_type object", "subsample_size": m, "draws": a.draws, "results": rows}
    a.out.write_text(json.dumps(out, indent=2))
    print(f"corpus={len(sents)} sentences, embedder={a.embedder}, subsample m={m}, draws={a.draws}  (lower is better)")
    print(f"{'KG':58s}{'triples':>8s}  {'full: fwd  bwd  sym':>22s}   {'size-matched: fwd  bwd  sym (sd)':>40s}")
    for r in rows:
        f, s, sd = r["full"], r[f"subsample_m{m}_mean"], r[f"subsample_m{m}_sd"]
        print(f"{r['kg']:58s}{r['n_triples']:>8d}  {f['fwd']:.3f} {f['bwd']:.3f} {f['sym']:.3f}      "
              f"{s['fwd']:.3f} {s['bwd']:.3f} {s['sym']:.3f} ({sd['fwd']:.3f} {sd['bwd']:.3f} {sd['sym']:.3f})")


if __name__ == "__main__":
    main()
