"""Prerequisite DIRECTION check against AL-CPL (independent labels), separate from edge existence and weights.

For every AL-CPL positive pair "B is a prerequisite of A" whose two concepts match distinct KG concepts, a method
"decides" a direction if it puts more evidence on one direction than the other:
  kg_edges     Prerequisite edge B->A vs A->B in relations.csv (pairs with an edge in exactly one direction)
  pair_scores  score_Prerequisite(B->A) vs (A->B) in pair_scores.csv, if present (pairs with unequal scores)
  book_order   B first mentioned before A in the textbook (pairs where both are located)
Reported: pairs decided, share decided correctly (B->A), Wilson 95% CI. Weights are not used: a symmetric weight
cannot decide direction. A KG whose run_meta.json says uses_book_order=true is flagged CIRCULAR for book order.

  python -m kg_eval.direction_check --kg-dir data_output/ck12_geometry_kgx_v2
"""

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from evaluate_prerequisite_extraction import build_extracted_concept_index, match_gold_concept

from .data import (DEFAULT_ALCPL_PAIRS, DEFAULT_ALCPL_PREQS, DEFAULT_SOURCE, concept_terms, first_position,
                   load_alcpl, load_kg, read_source)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (m - c, m + c)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kg-dir", type=Path, required=True)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--pairs", type=Path, default=DEFAULT_ALCPL_PAIRS)
    ap.add_argument("--preqs", type=Path, default=DEFAULT_ALCPL_PREQS)
    a = ap.parse_args()
    concepts, relations = load_kg(a.kg_dir)
    meta_path = a.kg_dir / "run_meta.json"
    uses_order = json.loads(meta_path.read_text()).get("uses_book_order", False) if meta_path.exists() else False
    gold = load_alcpl(a.pairs, a.preqs)
    gold = gold[gold.label == 1]
    by_id, term_to_cid, normalizer = build_extracted_concept_index(concepts)
    match = {g: match_gold_concept(g, term_to_cid, by_id, normalizer)[0]
             for g in set(gold.concept) | set(gold.prereq)}
    pre = set(zip(relations.loc[relations.relation_type == "Prerequisite", "source_id"],
                  relations.loc[relations.relation_type == "Prerequisite", "target_id"]))
    ps = None
    if (a.kg_dir / "pair_scores.csv").exists():
        df = pd.read_csv(a.kg_dir / "pair_scores.csv", dtype={"source_id": str, "target_id": str})
        ps = {(s, t): v for s, t, v in zip(df.source_id, df.target_id, df.score_Prerequisite)}
    text = read_source(a.source)
    terms = concept_terms(concepts)
    pos = {cid: first_position(t, text) for cid, t in terms.items()}

    tally = {"kg_edges": [0, 0], "pair_scores": [0, 0], "book_order": [0, 0]}
    n_pairs = 0
    for A, B in zip(gold.concept, gold.prereq):
        ca, cb = match.get(A), match.get(B)
        if not ca or not cb or ca == cb:
            continue
        n_pairs += 1
        fwd, back = (cb, ca) in pre, (ca, cb) in pre
        if fwd != back:
            tally["kg_edges"][0] += 1
            tally["kg_edges"][1] += fwd
        if ps is not None:
            sf, sb = ps.get((cb, ca), 0.0), ps.get((ca, cb), 0.0)
            if sf != sb:
                tally["pair_scores"][0] += 1
                tally["pair_scores"][1] += sf > sb
        if pos.get(ca) is not None and pos.get(cb) is not None and pos[ca] != pos[cb]:
            tally["book_order"][0] += 1
            tally["book_order"][1] += pos[cb] < pos[ca]
    out = {"kg_dir": str(a.kg_dir), "gold_positive_pairs_matched": n_pairs, "uses_book_order": uses_order}
    print(f"{a.kg_dir}: {n_pairs} AL-CPL positive pairs with both concepts matched"
          + ("   [KG built with book order: kg_edges/pair_scores vs book order are CIRCULAR]" if uses_order else ""))
    for k, (n, c) in tally.items():
        if k == "pair_scores" and ps is None:
            continue
        lo, hi = wilson(c, n)
        out[k] = {"decided": n, "correct": c, "accuracy": c / n if n else None, "wilson95": [lo, hi]}
        acc = f"{c / n:.3f} [{lo:.2f}, {hi:.2f}]" if n else "n/a"
        print(f"  {k:12s} decided {n:4d}  correct direction {c:4d}  accuracy {acc}")
    (a.kg_dir / "kg_eval").mkdir(exist_ok=True)
    (a.kg_dir / "kg_eval" / "direction_check_report.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
