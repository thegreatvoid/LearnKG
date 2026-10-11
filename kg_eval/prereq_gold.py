"""
Section 1: prerequisite correctness against the AL-CPL geometry benchmark (no LLM).

AL-CPL (Liang et al., AAAI 2018) gives 1681 labelled directed pairs (524 positive):
"is B a prerequisite of A?". A KG Prerequisite edge source -> target means
"source must be understood before target", so gold (A, B, 1) is recovered by an
edge B -> A. Reversed edges are NOT counted as correct (the older
evaluate_prerequisite_extraction.py counts them; that inflates its numbers).

Predictors, all scored on the same pairs:
  kg_prereq        Prerequisite edge B -> A (score = edge weight)      [main result]
  kg_closure       B reaches A through Prerequisite edges (score = 1/path length)
  kg_any_relation  edge of any relation type B -> A (score = max weight)
  kg_undirected    Prerequisite edge in either direction (diagnostic only, ignores direction)
  book_order       B first mentioned before A in the textbook
  cooccurrence     A and B mentioned in the same sentence (undirected)
  cooc_x_order     co-occurrence count, only when B appears before A
  refd_text        RefD (Liang et al. 2015) adapted to textbook sentences:
                   |S_A & S_B|/|S_A| - |S_A & S_B|/|S_B|

Evaluation sets:
  main        both gold concepts matched to distinct KG concepts AND located in the text
              (all predictors comparable here)
  end_to_end  all gold pairs; unmatched concepts count as "no edge" (KG predictors only)

Run from LearnKG/:
  python -m kg_eval.prereq_gold [--kg-dir data_output/ck12_geometry] [--out DIR]
"""

import argparse
import json
from pathlib import Path

import networkx as nx
import pandas as pd

from evaluate_prerequisite_extraction import (
    GEOMETRY_SYNONYM_MAP,
    build_extracted_concept_index,
    match_gold_concept,
    normalize_gold_concept_name,
)
from .data import (
    DEFAULT_KG_DIR,
    DEFAULT_SOURCE,
    auc,
    average_precision,
    bootstrap_ci,
    first_position,
    fmt,
    load_alcpl,
    load_kg,
    prf,
    read_source,
    split_sentences,
    term_pattern,
)

KG_PREDICTORS = ["kg_prereq", "kg_closure", "kg_any_relation", "kg_undirected"]
BASELINES = ["book_order", "cooccurrence", "cooc_x_order", "refd_text"]


def gold_text_terms(gold_name: str):
    base = normalize_gold_concept_name(gold_name)
    terms = [base]
    for key, syns in GEOMETRY_SYNONYM_MAP.items():
        if key.lower() == base.lower():
            terms += syns
    return terms


def kg_edge_maps(relations: pd.DataFrame):
    rel = relations.copy()
    rel["weight"] = pd.to_numeric(rel["weight"], errors="coerce").fillna(0.0)
    prereq, any_rel = {}, {}
    for s, t, rt, w in zip(rel["source_id"], rel["target_id"], rel["relation_type"], rel["weight"]):
        any_rel[(s, t)] = max(any_rel.get((s, t), w), w)
        if rt.strip().lower() == "prerequisite":
            prereq[(s, t)] = max(prereq.get((s, t), w), w)
    G = nx.DiGraph()
    G.add_edges_from(prereq)
    return prereq, any_rel, G


def score_pairs(gold, concepts, relations, text):
    concepts_by_id, term_to_cid, normalizer = build_extracted_concept_index(concepts)
    prereq, any_rel, G = kg_edge_maps(relations)
    sentences = split_sentences(text)

    names = sorted(set(gold["concept"]) | set(gold["prereq"]))
    match, pos, sents = {}, {}, {}
    for g in names:
        cid, conf, score, _ = match_gold_concept(g, term_to_cid, concepts_by_id, normalizer)
        match[g] = {"cid": cid, "kg_name": concepts_by_id[cid]["concept_name"] if cid else None, "confidence": conf}
        terms = gold_text_terms(g)
        pos[g] = first_position(terms, text)
        pats = [p for p in map(term_pattern, terms) if p]
        sents[g] = {i for i, s in enumerate(sentences) if any(p.search(s) for p in pats)}

    rows = []
    for a, b, label in zip(gold["concept"], gold["prereq"], gold["label"]):
        ca, cb = match[a]["cid"], match[b]["cid"]
        matched = bool(ca and cb and ca != cb)
        located = pos[a] is not None and pos[b] is not None
        r = {"concept": a, "prereq": b, "label": int(label),
             "kg_concept": match[a]["kg_name"], "kg_prereq_concept": match[b]["kg_name"],
             "matched": matched, "located": located}

        # KG predictors: score > 0 means predicted positive
        r["kg_prereq"] = prereq.get((cb, ca), 0.0) + 1.0 if matched and (cb, ca) in prereq else 0.0
        r["kg_any_relation"] = any_rel.get((cb, ca), 0.0) + 1.0 if matched and (cb, ca) in any_rel else 0.0
        r["kg_undirected"] = 1.0 if matched and ((cb, ca) in prereq or (ca, cb) in prereq) else 0.0
        r["kg_closure"] = 0.0
        if matched and cb in G and ca in G and nx.has_path(G, cb, ca):
            r["kg_closure"] = 1.0 / nx.shortest_path_length(G, cb, ca)

        # Text baselines
        sa, sb = sents[a], sents[b]
        both = len(sa & sb)
        b_first = located and pos[b] < pos[a]
        r["book_order"] = (pos[a] - pos[b]) / len(text) if located else 0.0
        r["cooccurrence"] = float(both)
        r["cooc_x_order"] = float(both) if b_first else 0.0
        r["refd_text"] = (both / len(sa) - both / len(sb)) if sa and sb else 0.0
        rows.append(r)
    return pd.DataFrame(rows), match


def evaluate(df: pd.DataFrame, predictors, reps: int):
    labels = df["label"].tolist()
    out = {"n_pairs": len(df), "n_positive": int(sum(labels)),
           "prevalence": sum(labels) / len(labels) if labels else float("nan")}
    for name in predictors:
        scores = df[name].tolist()
        pred = [int(s > 0) for s in scores]
        m = prf(pred, labels)
        m["f1_ci95"] = bootstrap_ci(lambda idx: prf([pred[i] for i in idx], [labels[i] for i in idx])["f1"], len(df), reps)
        m["roc_auc"] = auc(scores, labels)
        m["roc_auc_ci95"] = bootstrap_ci(lambda idx: auc([scores[i] for i in idx], [labels[i] for i in idx]), len(df), reps)
        m["pr_auc"] = average_precision(scores, labels)
        out[name] = m
    return out


def weight_only(df: pd.DataFrame):
    """Among pairs that already have a KG Prerequisite edge B -> A: does a higher weight mean 'more likely gold'?"""
    sub = df[df["kg_prereq"] > 0]
    return {"n": len(sub), "n_positive": int(sub["label"].sum()),
            "roc_auc": auc(sub["kg_prereq"].tolist(), sub["label"].tolist()),
            "note": "n is small; treat as descriptive"}


def print_table(title, res, predictors):
    print(f"\n{title}  (n={res['n_pairs']}, positives={res['n_positive']}, prevalence={fmt(res['prevalence'])})")
    print(f"  {'predictor':<16}{'P':>7}{'R':>7}{'F1':>7}  {'F1 95% CI':<15}{'MCC':>7}{'ROC-AUC':>9}  {'AUC 95% CI':<15}{'PR-AUC':>8}")
    for name in predictors:
        m = res[name]
        f_ci = f"[{fmt(m['f1_ci95'][0], 2)}, {fmt(m['f1_ci95'][1], 2)}]"
        a_ci = f"[{fmt(m['roc_auc_ci95'][0], 2)}, {fmt(m['roc_auc_ci95'][1], 2)}]"
        print(f"  {name:<16}{fmt(m['precision']):>7}{fmt(m['recall']):>7}{fmt(m['f1']):>7}  {f_ci:<15}"
              f"{fmt(m['mcc']):>7}{fmt(m['roc_auc']):>9}  {a_ci:<15}{fmt(m['pr_auc']):>8}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kg-dir", type=Path, default=DEFAULT_KG_DIR, help="folder with concepts.csv and relations.csv")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="textbook .txt")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: <kg-dir>/kg_eval)")
    ap.add_argument("--reps", type=int, default=1000, help="bootstrap resamples")
    args = ap.parse_args()
    out_dir = args.out or args.kg_dir / "kg_eval"
    out_dir.mkdir(parents=True, exist_ok=True)

    concepts, relations = load_kg(args.kg_dir)
    gold = load_alcpl()
    text = read_source(args.source)
    df, match = score_pairs(gold, concepts, relations, text)

    main_set = df[df["matched"] & df["located"]]
    res_main = evaluate(main_set, KG_PREDICTORS + BASELINES, args.reps)
    res_e2e = evaluate(df, KG_PREDICTORS, args.reps)

    n_gold = len(match)
    n_matched = sum(1 for m in match.values() if m["cid"])
    report = {
        "kg_dir": str(args.kg_dir),
        "gold": "AL-CPL geometry (geometry.pairs / geometry.preqs)",
        "gold_pairs": len(df), "gold_positive": int(df["label"].sum()),
        "gold_concepts": n_gold, "gold_concepts_matched_to_kg": n_matched,
        "gold_concepts_low_confidence_match": sorted(g for g, m in match.items() if m["confidence"] == "low"),
        "gold_concepts_unmatched": sorted(g for g, m in match.items() if not m["cid"]),
        "pairs_matched": int(df["matched"].sum()), "pairs_located_in_text": int(df["located"].sum()),
        "main": res_main,
        "end_to_end": res_e2e,
        "kg_prereq_weight_only": weight_only(main_set),
        "kg_prereq_edges_reversed_vs_gold": int(((df["kg_undirected"] > 0) & (df["kg_prereq"] == 0) & (df["label"] == 1)).sum()),
        "concept_matches": match,
        "notes": [
            "Direction is strict: an edge A -> B for gold 'B is a prerequisite of A' is counted as wrong.",
            "Bootstrap is over pairs; pairs share concepts, so CIs are somewhat optimistic.",
            "kg_undirected ignores direction and is a diagnostic, not a correctness score.",
        ],
    }
    (out_dir / "prereq_gold_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    df.to_csv(out_dir / "prereq_gold_pairs.csv", index=False)

    print(f"Gold concepts matched to KG: {n_matched}/{n_gold};  pairs matched: {report['pairs_matched']}/{len(df)};"
          f"  located in text: {report['pairs_located_in_text']}")
    print_table("MAIN (matched & located pairs)", res_main, KG_PREDICTORS + BASELINES)
    print_table("END-TO-END (all AL-CPL pairs, KG only)", res_e2e, KG_PREDICTORS)
    w = report["kg_prereq_weight_only"]
    print(f"\nWeight-only AUC among pairs with a KG Prerequisite edge: {fmt(w['roc_auc'])} (n={w['n']}, positives={w['n_positive']})")
    print(f"Gold positives with a KG Prerequisite edge pointing the WRONG way: {report['kg_prereq_edges_reversed_vs_gold']}")
    print(f"\nWrote {out_dir / 'prereq_gold_report.json'} and prereq_gold_pairs.csv")


if __name__ == "__main__":
    main()
