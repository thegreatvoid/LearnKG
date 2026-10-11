"""B. Edge-weight validity. Target construct: educational relevance for localized graph construction
(NOT factual confidence).

  python -m kg_eval.weight_validity sample --n 90
  python -m kg_eval.weight_validity rate   --reps 2        # blind LLM ratings 1-5
  python -m kg_eval.weight_validity analyze
"""

import argparse
import json
import random
from pathlib import Path

import pandas as pd

from .data import (DEFAULT_GOLD, DEFAULT_KG_DIR, DEFAULT_OUT, DEFAULT_SOURCE, auc, bootstrap_ci, edge_table, fmt,
                   load_kg, norm_name, read_source, spearman)

MIN_N_PER_TYPE = 10


def stratified_sample(edges, n, seed=0):
    rng = random.Random(seed)
    edges = edges.copy()
    edges["wbin"] = pd.qcut(edges["weight"].rank(method="first"), 3, labels=["low", "mid", "high"])
    strata = [g.index.tolist() for _, g in edges.groupby(["relation_type", "wbin"], observed=True)]
    for s in strata:
        rng.shuffle(s)
    picked = []
    while len(picked) < min(n, len(edges)) and any(strata):  # round-robin so small strata are represented
        for s in strata:
            if s and len(picked) < n:
                picked.append(s.pop())
    return edges.loc[picked]


def load_ratings(path, model=None):
    """{relation_id: {rep: rating}} for one judge model (default: the configured Ollama judge)."""
    from .data import read_jsonl
    from .judge import OLLAMA_MODEL
    model = model or OLLAMA_MODEL
    by = {}
    for r in read_jsonl(path):
        if r["key"].startswith(f"rate:{model}:"):
            _, _, rid, rep = r["key"].rsplit(":", 3)
            by.setdefault(rid, {})[int(rep)] = r["rating"]
    return by


def cmd_sample(a, edges, out):
    s = stratified_sample(edges, a.n, a.seed)
    s[["relation_id", "relation_type", "source_name", "target_name", "evidence", "weight"]].to_csv(
        out / "weight_sample.csv", index=False)
    print(f"wrote {len(s)} edges to {out/'weight_sample.csv'}")
    print(s.groupby("relation_type").size().to_dict())


def cmd_rate(a, edges, out):
    from .judge import Judge
    sample = pd.read_csv(out / "weight_sample.csv", dtype=str, keep_default_na=False)
    e = edges.set_index("relation_id")
    judge = Judge(read_source(a.source), out / "judge_cache.jsonl")
    for rid in sample["relation_id"]:
        row = e.loc[rid].copy()
        row["relation_id"] = rid
        for rep in range(a.reps):
            try:
                print(rid, rep, judge.rate(row, rep)["rating"])
            except RuntimeError as exc:
                print(rid, rep, "JUDGE_ERROR", exc)


def cmd_analyze(a, edges, out):
    sample = pd.read_csv(out / "weight_sample.csv", dtype=str, keep_default_na=False)
    ratings = load_ratings(out / "judge_cache.jsonl")
    df = edges[edges.relation_id.isin(sample.relation_id)].copy()
    df = df[df.relation_id.isin(ratings)]
    df["rating"] = [sum(ratings[r].values()) / len(ratings[r]) for r in df.relation_id]
    report = {"n_rated": len(df)}

    reps = [list(ratings[r].values()) for r in df.relation_id if len(ratings[r]) >= 2]
    if reps:  # inter-rater proxy: agreement between repeated independent LLM ratings
        report["rater_test_retest_spearman"] = spearman([r[0] for r in reps], [r[1] for r in reps])

    def rho_ci(sub):
        w, y = sub["weight"].tolist(), sub["rating"].tolist()
        lo, hi = bootstrap_ci(lambda idx: spearman([w[i] for i in idx], [y[i] for i in idx]), len(sub))
        return {"n": len(sub), "rho": spearman(w, y), "ci95": [lo, hi],
                "reliable": len(sub) >= MIN_N_PER_TYPE}

    report["overall"] = rho_ci(df)
    report["per_relation_type"] = {t: rho_ci(g) for t, g in df.groupby("relation_type")}

    # high vs low weight (top vs bottom tercile) on support, coverage, downstream usefulness
    supp_path = out / "support_judgments.csv"
    if supp_path.exists():
        df = df.merge(pd.read_csv(supp_path)[["relation_id", "label"]], on="relation_id", how="left")
    q1, q2 = df["weight"].quantile([1 / 3, 2 / 3])
    df["tier"] = df["weight"].apply(lambda w: "low" if w <= q1 else ("high" if w > q2 else "mid"))
    gold = pd.read_csv(DEFAULT_GOLD, dtype=str, keep_default_na=False)
    gold_pairs = {(norm_name(x), norm_name(y)) for x, y, t in zip(gold.concept_a, gold.concept_b, gold.relation_type)
                  if t == "Prerequisite"}
    df["gold_match"] = [int(t == "Prerequisite" and (norm_name(s), norm_name(d)) in gold_pairs)
                        for t, s, d in zip(df.relation_type, df.source_name, df.target_name)]
    tiers = {}
    for tier, g in df.groupby("tier"):
        t = {"n": len(g), "mean_rating": g["rating"].mean(), "frac_rating_ge4": float((g["rating"] >= 4).mean()),
             "concepts_covered": len(set(g.source_id) | set(g.target_id)),
             "gold_prereq_hits": int(g["gold_match"].sum())}
        if "label" in g:
            t["frac_supported"] = float((g["label"] == "Supported").mean())
        tiers[tier] = t
    report["weight_tiers"] = tiers
    report["caveat"] = ("Ratings come from an LLM judge; correlation with them is evidence about the weight's "
                        "alignment with that construct, not proof the weights improve the KG. See ablation (C).")
    (out / "weight_validity_report.json").write_text(json.dumps(report, indent=2, default=float))
    print(f"n_rated={report['n_rated']}  overall rho={fmt(report['overall']['rho'])} "
          f"CI={[fmt(x) for x in report['overall']['ci95']]}")
    for t, v in report["per_relation_type"].items():
        print(f"  {t:13s} n={v['n']:3d} rho={fmt(v['rho'])} CI={[fmt(x) for x in v['ci95']]}"
              f"{'' if v['reliable'] else '  (n too small)'}")
    print("tiers:", json.dumps(tiers, indent=1, default=float))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "rate", "analyze"])
    ap.add_argument("--kg-dir", default=str(DEFAULT_KG_DIR))
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--n", type=int, default=90)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--reps", type=int, default=2)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    concepts, relations = load_kg(Path(a.kg_dir))
    edges = edge_table(concepts, relations)
    {"sample": cmd_sample, "rate": cmd_rate, "analyze": cmd_analyze}[a.cmd](a, edges, out)


if __name__ == "__main__":
    main()
