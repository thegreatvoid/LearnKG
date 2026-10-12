"""Concept-extraction quality (no LLM, no humans).

  python -m kg_eval.concept_quality --kg-dir data_output/ck12_geometry_kgx_cand

Reports: concepts found verbatim in the textbook (hallucination = 1 - rate); recall of AL-CPL gold concepts
(a matching KG concept exists; high-confidence matches reported separately); and, if candidate_pairs.csv or
pair_scores.csv exists, how many gold positive pairs the pair generator even considered (an upper bound on recall).
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from evaluate_prerequisite_extraction import build_extracted_concept_index, match_gold_concept
from .data import DEFAULT_KG_DIR, DEFAULT_SOURCE, fmt, load_alcpl, load_kg, read_source


def _norm(s):
    import re
    return " " + " ".join(re.findall(r"[a-z0-9]+", str(s).lower())) + " "


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kg-dir", type=Path, default=DEFAULT_KG_DIR)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    out = a.out or a.kg_dir / "kg_eval"
    out.mkdir(parents=True, exist_ok=True)

    concepts, _ = load_kg(a.kg_dir)
    text = _norm(read_source(a.source))
    # singular/plural tolerant verbatim test
    def found(name):
        n = _norm(name).strip()
        return bool(n) and any(v in text for v in (f" {n} ", f" {n}s ", f" {n}es ", f" {n.rstrip('s')} "))
    verbatim = [found(n) for n in concepts["concept_name"]]

    gold = load_alcpl()
    by_id, term_to_cid, normalizer = build_extracted_concept_index(concepts)
    names = sorted(set(gold["concept"]) | set(gold["prereq"]))
    match = {g: match_gold_concept(g, term_to_cid, by_id, normalizer) for g in names}
    matched = {g for g, m in match.items() if m[0]}
    high = {g for g, m in match.items() if m[0] and m[1] == "high"}

    rep = {"kg_dir": str(a.kg_dir), "n_concepts": len(concepts),
           "verbatim_in_text_rate": sum(verbatim) / max(1, len(verbatim)),
           "not_verbatim_examples": [n for n, v in zip(concepts["concept_name"], verbatim) if not v][:15],
           "gold_concepts": len(names), "gold_concept_recall_any": len(matched) / len(names),
           "gold_concept_recall_high_confidence": len(high) / len(names),
           "gold_concepts_missing": sorted(set(names) - matched)}

    for fname in ("pair_scores.csv", "candidate_pairs.csv"):
        f = a.kg_dir / fname
        if f.exists():
            cp = pd.read_csv(f, dtype=str)
            pairs = {(s, t) for s, t in zip(cp["source_id"], cp["target_id"])}
            pairs |= {(t, s) for s, t in pairs}
            pos = gold[gold["label"] == 1]
            cov = tot = 0
            for g_a, g_b in zip(pos["concept"], pos["prereq"]):
                ca, cb = match[g_a][0], match[g_b][0]
                if ca and cb and ca != cb:
                    tot += 1
                    cov += (ca, cb) in pairs
            rep["pair_candidate_file"] = fname
            rep["gold_positive_pairs_with_both_concepts"] = tot
            rep["gold_positive_pairs_considered_by_generator"] = cov
            rep["candidate_recall_upper_bound"] = cov / tot if tot else None
            break
    (out / "concept_quality_report.json").write_text(json.dumps(rep, indent=2, default=str))
    print(f"concepts={rep['n_concepts']}  verbatim in text={fmt(rep['verbatim_in_text_rate'])}")
    print(f"AL-CPL concept recall: any={fmt(rep['gold_concept_recall_any'])}  high-confidence={fmt(rep['gold_concept_recall_high_confidence'])}"
          f" ({len(matched)}/{len(names)})")
    if "candidate_recall_upper_bound" in rep:
        print(f"gold positive pairs considered by pair generator: {rep['gold_positive_pairs_considered_by_generator']}/"
              f"{rep['gold_positive_pairs_with_both_concepts']} = {fmt(rep['candidate_recall_upper_bound'])}")
    print("missing gold concepts:", rep["gold_concepts_missing"][:20])


if __name__ == "__main__":
    main()
