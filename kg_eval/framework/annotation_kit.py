"""Phase 9: annotation package for relation types without reference labels, plus agreement and evaluation tools.

  python -m kg_eval.framework.annotation_kit build
  python -m kg_eval.framework.annotation_kit agreement annotator_A.csv annotator_B.csv
  python -m kg_eval.framework.annotation_kit evaluate adjudicated.csv

`build` writes a BLIND item file (concept pairs in random order, supporting sentences, no predicted type or source)
and a separate KEY file (where each item came from). Items: predicted edges of every type from rule_v3, kgx_v2 and
kgx_v2_hybrid; hard negatives (pairs mentioned in the same sentence that no KG relates); the gold_pairs.csv pilot
pairs (re-annotated, not trusted); AL-CPL calibration pairs (to check annotators against an independent reference).
`evaluate` accepts ONLY an adjudicated, human-labelled file (common.load_reference); it never uses predictions as
labels, and reports results as measured on the annotated SAMPLE, not on the whole graph.
"""

import argparse
import random
import re
import sys
from pathlib import Path

import pandas as pd

from .common import (KG, RELATION_TYPES, ROOT, book_chunks, book_sentences, gold, load_reference, out_dir, prf,
                     wilson, write_json)

LABELS = RELATION_TYPES + ["None", "Unsure"]
DIRECTIONS = ["A->B", "B->A", "undirected", "n/a"]
PER_TYPE = 40
HARD_NEG = 60
CALIBRATION = 20
SOURCE_KGS = ["rule_v3", "kgx_v2", "kgx_v2_hybrid"]


def _re(name):
    w = re.findall(r"[a-z0-9]+", name.lower())
    return re.compile(r"\b" + r"[\s\-]+".join(map(re.escape, w)) + r"(?:s|es)?\b", re.I) if w else None


def support(a, b, sents, k=3):
    ra, rb = _re(a), _re(b)
    return [s for s in sents if ra and rb and ra.search(s) and rb.search(s)][:k]


def first_sentence(a, sents):
    ra = _re(a)
    return next((s for s in sents if ra and ra.search(s)), "")


def section_of(a, b):
    ra, rb = _re(a), _re(b)
    for ch in book_chunks():
        if ra and rb and ra.search(ch.text) and rb.search(ch.text):
            return ch.section
    return ""


def build(seed=0):
    rng = random.Random(seed)
    sents = book_sentences()
    items, seen = [], set()

    def add(a, b, origin):
        key = frozenset((a.lower(), b.lower()))
        if a.lower() == b.lower() or key in seen:
            return False
        seen.add(key)
        first, second = (a, b) if rng.random() < 0.5 else (b, a)
        items.append({"concept_A": first, "concept_B": second, "origin": origin,
                      "orig_source": a, "orig_target": b, "support": support(first, second, sents),
                      "section": section_of(first, second)})
        return True

    # 1. predicted edges, stratified by type and KG
    for ty in RELATION_TYPES:
        pool = []
        for name in SOURCE_KGS:
            kg = KG(name)
            d = kg.relations[kg.relations.relation_type == ty]
            pool += [(kg.name_of[s], kg.name_of[t], name) for s, t in zip(d.source_id, d.target_id)]
        rng.shuffle(pool)
        n = 0
        for s, t, name in pool:
            if n >= (CALIBRATION if ty == "Prerequisite" else PER_TYPE):
                break
            n += add(s, t, f"predicted:{name}:{ty}")
    # 2. hard negatives: same sentence, no relation in any source KG
    related = set()
    names = {}
    for name in SOURCE_KGS:
        kg = KG(name)
        for s, t in zip(kg.relations.source_id, kg.relations.target_id):
            related.add(frozenset((kg.name_of[s].lower(), kg.name_of[t].lower())))
        names.update({n.lower(): n for n in kg.concepts.concept_name})
    cands = []
    regs = {n: _re(n) for n in names}
    for s in sents:
        present = sorted(n for n, r in regs.items() if r and r.search(s))
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                if frozenset((present[i], present[j])) not in related:
                    cands.append((names[present[i]], names[present[j]]))
    rng.shuffle(cands)
    n = 0
    for a, b in cands:
        if n >= HARD_NEG:
            break
        n += add(a, b, "hard_negative:co-mentioned, no KG relation")
    # 3. pilot pairs (re-annotation of gold_pairs.csv; not trusted as labels)
    pilot = pd.read_csv(ROOT / "data_input/ck12_geometry/gold_pairs.csv", keep_default_na=False)
    for a, b, ty in zip(pilot.concept_a, pilot.concept_b, pilot.relation_type):
        add(a, b, f"pilot_gold_pairs:{ty}")
    # 4. AL-CPL calibration (independent prerequisite labels)
    g = gold()
    sample = g.sample(n=CALIBRATION, random_state=seed)
    for a, b, y in zip(sample.concept, sample.prereq, sample.label):
        add(b.replace("_", " "), a.replace("_", " "), f"alcpl_calibration:{'prerequisite' if y else 'not_prerequisite'}")

    rows, key = [], []
    for i, it in enumerate(items, 1):
        iid = f"R{i:04d}"
        sup = it["support"] + [""] * (3 - len(it["support"]))
        rows.append({"item_id": iid, "concept_A": it["concept_A"], "concept_B": it["concept_B"],
                     "supporting_text_1": sup[0], "supporting_text_2": sup[1], "supporting_text_3": sup[2],
                     "context_A": first_sentence(it["concept_A"], sents), "context_B": first_sentence(it["concept_B"], sents),
                     "section": it["section"], "relation": "", "direction": "", "confidence_1to3": "",
                     "annotator_id": "", "notes": ""})
        direction = "A->B" if it["concept_A"] == it["orig_source"] else "B->A"
        key.append({"item_id": iid, "origin": it["origin"], "origin_direction_in_item": direction})
    d = out_dir("annotation", "relations")
    pd.DataFrame(rows).to_csv(d / "relation_items_BLIND.csv", index=False)
    pd.DataFrame(key).to_csv(d / "relation_items_KEY_do_not_show_annotators.csv", index=False)
    write_json(d / "build_summary.json", {"items": len(rows), "seed": seed,
                                          "by_origin": pd.Series([k["origin"].split(":")[0] + (":" + k["origin"].split(":")[2]
                                                                  if k["origin"].startswith("predicted") else "")
                                                                  for k in key]).value_counts().to_dict()})
    import shutil
    shutil.copy(Path(__file__).with_name("ANNOTATION_GUIDELINES.md"), d.parent / "ANNOTATION_GUIDELINES.md")
    q = out_dir("annotation", "questions")
    pd.DataFrame(columns=["question_id", "question_text", "target_concept", "expected_prerequisites",
                          "reference_source", "expert_id", "simulated_known_concepts",
                          "expected_missing_prerequisites", "notes"]).to_csv(q / "questions_TEMPLATE.csv", index=False)
    print(f"wrote {len(rows)} blind items to {d}")


def kappa(a, b):
    a, b = list(a), list(b)
    n = len(a)
    if n == 0:
        return float("nan")
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def agreement(path_a, path_b):
    A = pd.read_csv(path_a, dtype=str, keep_default_na=False).set_index("item_id")
    B = pd.read_csv(path_b, dtype=str, keep_default_na=False).set_index("item_id")
    both = [i for i in A.index if i in B.index and A.loc[i, "relation"] and B.loc[i, "relation"]]
    ra, rb = [A.loc[i, "relation"] for i in both], [B.loc[i, "relation"] for i in both]
    same_dir = [i for i in both if A.loc[i, "relation"] == B.loc[i, "relation"] and A.loc[i, "relation"] in
                ("Prerequisite", "Part-of", "Application", "Extension")]
    res = {"items_both_annotated": len(both), "relation_kappa": kappa(ra, rb),
           "relation_raw_agreement": sum(x == y for x, y in zip(ra, rb)) / len(both) if both else None,
           "direction_agreement_when_same_directed_relation":
               sum(A.loc[i, "direction"] == B.loc[i, "direction"] for i in same_dir) / len(same_dir) if same_dir else None,
           "items_needing_adjudication": [i for i in both if A.loc[i, "relation"] != B.loc[i, "relation"]
                                          or A.loc[i, "direction"] != B.loc[i, "direction"]]}
    print({k: v for k, v in res.items() if k != "items_needing_adjudication"},
          f"| {len(res['items_needing_adjudication'])} items to adjudicate")
    return res


def confusion(ref, idx, rel, ty):
    """TP/FP/FN for relation type `ty` on adjudicated items. `ref` rows: concept_A, concept_B, adjudicated_relation,
    adjudicated_direction (A->B / B->A / undirected). `idx`: lowercased concept name -> KG id. `rel`: set of
    (source_id, target_id, type). Similarity is undirected (either stored direction counts); for directed types a
    predicted edge in the wrong direction counts as one FP and one FN (and a direction error). Items whose concepts
    are not both in the KG are skipped (reported as not covered), never counted as negatives."""
    tp = fp = fn = dir_err = covered = 0
    for _, r in ref.iterrows():
        a, b = idx.get(str(r.concept_A).lower()), idx.get(str(r.concept_B).lower())
        if not a or not b:
            continue
        covered += 1
        pred_ab, pred_ba = (a, b, ty) in rel, (b, a, ty) in rel
        pred = pred_ab or pred_ba
        is_ref = r.adjudicated_relation == ty
        if ty == "Similarity":
            right_dir = True
        else:
            want_ab = r.adjudicated_direction == "A->B"
            right_dir = (pred_ab and want_ab) or (pred_ba and not want_ab)
        if pred and is_ref and right_dir:
            tp += 1
        elif pred and is_ref:
            fp += 1
            fn += 1
            dir_err += 1
        elif pred:
            fp += 1
        elif is_ref:
            fn += 1
    return tp, fp, fn, dir_err, covered


def evaluate(adjudicated, key_path=None):
    """Per KG and relation type, on the annotated sample: TP/FP/FN, precision/recall/F1 (Wilson CI), direction errors."""
    ref = load_reference(Path(adjudicated), label_col="adjudicated_relation", allowed=LABELS)
    if "adjudicated_direction" not in ref.columns:
        raise ValueError("adjudicated file needs an adjudicated_direction column")
    items = pd.read_csv(out_dir("annotation", "relations") / "relation_items_BLIND.csv", dtype=str, keep_default_na=False)
    ref = ref.merge(items[["item_id", "concept_A", "concept_B"]], on="item_id", how="left")
    if ref.concept_A.isna().any():
        raise ValueError("adjudicated file contains item_ids that are not in relation_items_BLIND.csv")
    ref = ref[ref.adjudicated_relation != "Unsure"]
    res = {"scope": "annotated sample only (stratified, includes hard negatives): not whole-graph precision/recall",
           "items_used": len(ref), "kgs": {}}
    for name in SOURCE_KGS + ["rule_2026-10-11"]:
        kg = KG(name)
        idx = {n.lower(): c for c, n in kg.name_of.items()}
        rel = {(s, t, ty) for s, t, ty in zip(kg.relations.source_id, kg.relations.target_id, kg.relations.relation_type)}
        out = {}
        for ty in RELATION_TYPES:
            tp, fp, fn, dir_err, covered = confusion(ref, idx, rel, ty)
            m = prf(tp, fp, fn)
            m["precision_wilson95"] = wilson(tp, tp + fp)
            m["recall_wilson95"] = wilson(tp, tp + fn)
            m["direction_errors"] = dir_err
            m["items_with_both_concepts_in_kg"] = covered
            out[ty] = m
        res["kgs"][name] = out
    write_json(out_dir("annotation", "relations") / "annotation_evaluation.json", res)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    p = sub.add_parser("agreement"); p.add_argument("a"); p.add_argument("b")
    p = sub.add_parser("evaluate"); p.add_argument("adjudicated")
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    elif a.cmd == "agreement":
        agreement(a.a, a.b)
    else:
        evaluate(a.adjudicated)


if __name__ == "__main__":
    sys.exit(main())
