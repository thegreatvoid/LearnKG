"""A. Source-grounded KG quality. Four reports, kept separate on purpose:
  1. judged support (LLM, conditioned on the textbook)
  2. BIGS (Lermanda et al., ESWC 2026): unsupervised source alignment, both directions + Sym-BIGS
  3. coverage (what the KG reaches of the textbook / gold pairs)
  4. structural validity (duplicates, bad refs, malformed rows, cycles)
Support does not imply completeness; structural validity does not imply factual accuracy.

Usage: python -m kg_eval.source_quality [--no-judge] [--limit N]
"""

import argparse
import json
import re
from collections import Counter, defaultdict

import networkx as nx
import pandas as pd

from .bigs import DEFAULT_EMBEDDER, bigs, verbalize_triple
from .data import (DEFAULT_GOLD, DEFAULT_KG_DIR, DEFAULT_OUT, DEFAULT_SOURCE, edge_table, fmt, load_kg,
                   norm_name, read_source, split_sentences)

VALID_TYPES = {"Prerequisite", "Part-of", "Application", "Extension", "Similarity"}
HIERARCHY_TYPES = ("Prerequisite", "Part-of")
def structural_checks(concepts, relations):
    ids = set(concepts["concept_id"])
    out = defaultdict(list)
    seen = Counter()
    for _, r in relations.iterrows():
        rid = r["relation_id"]
        for col in ("relation_id", "source_id", "target_id", "relation_type", "evidence"):
            if not str(r[col]).strip():
                out["malformed"].append(f"{rid}: empty {col}")
        w = pd.to_numeric(r["weight"], errors="coerce")
        if pd.isna(w) or not 0 <= w <= 1:
            out["malformed"].append(f"{rid}: weight {r['weight']!r} not in [0,1]")
        if r["relation_type"] not in VALID_TYPES:
            out["malformed"].append(f"{rid}: unknown relation_type {r['relation_type']!r}")
        for col in ("source_id", "target_id"):
            if r[col] not in ids:
                out["invalid_reference"].append(f"{rid}: {col}={r[col]!r} not in concepts")
        if r["source_id"] == r["target_id"]:
            out["self_loop"].append(rid)
        seen[(r["source_id"], r["target_id"], r["relation_type"])] += 1
    out["duplicate_edge"] = [f"{k} x{v}" for k, v in seen.items() if v > 1]
    for k, v in Counter(relations["relation_id"]).items():
        if v > 1:
            out["duplicate_relation_id"].append(k)
    dup_names = Counter(norm_name(n) for n in concepts["concept_name"])
    out["duplicate_concept_name"] = [n for n, v in dup_names.items() if v > 1]
    for t in HIERARCHY_TYPES:
        g = nx.DiGraph()
        g.add_edges_from(relations.loc[relations["relation_type"] == t, ["source_id", "target_id"]].values)
        cyc = [c for c in nx.simple_cycles(g) if len(c) > 1] if not nx.is_directed_acyclic_graph(g) else []
        out[f"cycle_{t}"] = [" -> ".join(c) for c in cyc[:20]]
    return {k: {"count": len(v), "examples": v[:5]} for k, v in out.items()} | {
        k: {"count": 0, "examples": []} for k in
        ["malformed", "invalid_reference", "self_loop", "duplicate_edge", "duplicate_relation_id",
         "duplicate_concept_name", "cycle_Prerequisite", "cycle_Part-of"] if k not in out}


def coverage(concepts, edges, sentences, gold_path):
    names = {norm_name(n): cid for cid, n in zip(concepts["concept_id"], concepts["concept_name"])}
    touched = set(edges["source_id"]) | set(edges["target_id"])
    mention = [{cid for n, cid in names.items() if n and re.search(rf"\b{re.escape(n)}\b", norm_name(s))}
               for s in sentences]
    with_concept = [m for m in mention if m]
    in_edges = [m for m in with_concept if m & touched]
    evidence_text = " ".join(edges["evidence"]).lower()
    covered_sents = sum(1 for s in sentences if s.lower()[:80] in evidence_text)
    res = {
        "concepts_total": len(concepts),
        "concepts_in_any_edge": len(touched & set(concepts["concept_id"])),
        "concept_edge_participation": len(touched) / max(1, len(concepts)),
        "source_sentences": len(sentences),
        "sentences_mentioning_a_kg_concept": len(with_concept),
        "of_those_with_an_edge_concept": len(in_edges),
        "sentences_used_as_edge_evidence": covered_sents,
    }
    gold = pd.read_csv(gold_path, dtype=str, keep_default_na=False)
    gp = gold[gold["relation_type"] == "Prerequisite"]
    kg_pairs = {(norm_name(r.source_name), norm_name(r.target_name)) for r in edges.itertuples()
                if r.relation_type == "Prerequisite"}
    kg_pairs_any = kg_pairs | {(b, a) for a, b in kg_pairs}
    hit = sum((norm_name(a), norm_name(b)) in kg_pairs for a, b in zip(gp.concept_a, gp.concept_b))
    hit_undirected = sum((norm_name(a), norm_name(b)) in kg_pairs_any for a, b in zip(gp.concept_a, gp.concept_b))
    res.update(gold_prereq_pairs=len(gp), gold_recalled_directed=hit, gold_recalled_undirected=hit_undirected,
               gold_recall_directed=hit / max(1, len(gp)))
    return res


def support_summary(df):
    counts = Counter(df["label"])
    n = len(df)
    return {"n": n, "counts": dict(counts), "rates": {k: v / n for k, v in counts.items()},
            "by_relation_type": {t: dict(Counter(g["label"])) for t, g in df.groupby("relation_type")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg-dir", default=str(DEFAULT_KG_DIR))
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--gold", default=str(DEFAULT_GOLD))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--embedder", default=DEFAULT_EMBEDDER)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    from pathlib import Path
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    concepts, relations = load_kg(Path(a.kg_dir))
    text = read_source(a.source)
    sentences = split_sentences(text)
    edges = edge_table(concepts, relations)
    if a.limit:
        edges = edges.head(a.limit)

    report = {
        "structural": structural_checks(concepts, relations),
        "coverage": coverage(concepts, edges, sentences, a.gold),
    }
    b = bigs(sentences, [verbalize_triple(r.source_name, r.relation_type, r.target_name) for r in edges.itertuples()],
             a.embedder)
    edges["bigs_distance"] = b.pop("per_triple_distance")  # per-triple BIGS<- (lower = better grounded)
    b.pop("per_doc_unit_distance")
    report["bigs"] = b | {"note": "cosine distances; lower is better. relation_type is used as the predicate."}
    if not a.no_judge:
        from .judge import Judge
        judge = Judge(text, out / "judge_cache.jsonl")
        rows = []
        for _, e in edges.iterrows():
            try:
                j = judge.support(e)
            except RuntimeError as exc:
                print(e["relation_id"], "JUDGE_ERROR", exc)
                continue
            rows.append({"relation_id": e["relation_id"], "relation_type": e["relation_type"],
                         "bigs_distance": e["bigs_distance"], "label": j["label"], "quote": j["quote"],
                         "rationale": j["rationale"]})
            print(f'{e["relation_id"]} {j["label"]}')
        jd = pd.DataFrame(rows)
        jd.to_csv(out / "support_judgments.csv", index=False)
        report["judged_support"] = support_summary(jd)
        report["bigs_distance_by_judged_label"] = {
            lab: float(jd.loc[jd.label == lab, "bigs_distance"].mean()) for lab in jd.label.unique()}
    (out / "source_quality_report.json").write_text(json.dumps(report, indent=2, default=float))
    s = report["structural"]
    print("\nSTRUCTURAL:", {k: v["count"] for k, v in s.items()})
    print("COVERAGE:", report["coverage"])
    print("BIGS:", {k: round(v, 4) for k, v in report["bigs"].items() if isinstance(v, float)})
    if "judged_support" in report:
        print("SUPPORT:", {k: fmt(v) for k, v in report["judged_support"]["rates"].items()})


if __name__ == "__main__":
    main()
