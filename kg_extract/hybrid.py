"""Hybrid knowledge-graph construction (no gold labels used anywhere).

Takes a finished `kg_extract.run` folder (grounded concepts + LLM relation scores) and the source text, then:
  1. scores EVERY directed concept pair u -> v ("u is a prerequisite of v") from text-only signals:
       order    forward-only gate: u's first mention precedes v's, scaled by the gap
       cooc     sentences mentioning both
       refd     RefD (Liang et al. 2015) over sentence sets
       llm_rel  the run's LLM relatedness (sum of its relation scores, either direction), if available
     score = forward_gate * mean of the percentile ranks of the available signals (fixed equal weights).
  2. keeps, for each concept, its top-k predecessors that are also *related* (cooc > 0 or LLM-related), so
     early foundational concepts do not become prerequisites of everything;
  3. adds the LLM's non-Prerequisite relations (Part-of, Application, Extension, Similarity) for pairs without a
     Prerequisite edge.
Book order IS used as a signal here (recorded in run_meta.json: uses_book_order = true); do not report
`kg_eval.book_order` direction checks on this KG's own book.

  python -m kg_extract.hybrid --run data_output/ck12_geometry_kgx_run1 --out data_output/ck12_geometry_kgx_hybrid
"""

import argparse
import json
import re
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from kg_eval.data import DEFAULT_SOURCE, concept_terms, first_position, read_source, split_sentences, term_pattern

REL_COLS = ["Prerequisite", "Part-of", "Application", "Extension", "Similarity"]


def rank01(x: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] over the positive entries; zeros stay 0."""
    out = np.zeros_like(x, dtype=float)
    pos = x > 0
    if pos.any():
        r = pd.Series(x[pos]).rank(method="average").values
        out[pos] = r / r.max()
    return out


def build(run_dir: Path, source: Path, out: Path, top_k: int = 3, min_score: float = 0.0):
    text = read_source(source)
    concepts = pd.read_csv(run_dir / "concepts.csv", dtype=str, keep_default_na=False)
    ids = concepts["concept_id"].tolist()
    n = len(ids)
    terms = concept_terms(concepts)

    pos = {c: first_position(terms[c], text) for c in ids}
    sents = split_sentences(text)
    sets = {}
    for c in ids:
        pats = [p for p in map(term_pattern, terms[c]) if p]
        sets[c] = {i for i, s in enumerate(sents) if any(p.search(s) for p in pats)}

    # LLM relatedness (symmetric) from the run, if present
    llm = {}
    ps_path = run_dir / "pair_scores.csv"
    if ps_path.exists():
        ps = pd.read_csv(ps_path, dtype={"source_id": str, "target_id": str})
        rel_cols = [c for c in ps.columns if c.startswith("score_")]
        tot = ps[rel_cols].sum(axis=1)
        for s, t, v in zip(ps.source_id, ps.target_id, tot):
            k = frozenset((s, t))
            llm[k] = max(llm.get(k, 0.0), float(v))

    L = len(text)
    gap = np.zeros((n, n)); cooc = np.zeros((n, n)); refd = np.zeros((n, n)); rel = np.zeros((n, n))
    for i, u in enumerate(ids):
        for j, v in enumerate(ids):
            if i == j:
                continue
            both = len(sets[u] & sets[v])
            cooc[i, j] = both
            if sets[u] and sets[v]:
                refd[i, j] = max(0.0, both / len(sets[v]) - both / len(sets[u]))  # u explains v more than v explains u
            rel[i, j] = llm.get(frozenset((u, v)), 0.0)
            if pos[u] is not None and pos[v] is not None and pos[u] < pos[v]:
                gap[i, j] = (pos[v] - pos[u]) / L
    forward = gap > 0
    signals = {"order": rank01(gap), "cooc": rank01(cooc), "refd": rank01(refd)}
    if llm:
        signals["llm_rel"] = rank01(rel)
    score = np.mean([s for s in signals.values()], axis=0) * forward

    related = (cooc > 0) | (rel > 0)
    rows = []
    for i, u in enumerate(ids):
        for j, v in enumerate(ids):
            if i != j:
                rows.append((u, v, float(score[i, j])))
    pair = pd.DataFrame(rows, columns=["source_id", "target_id", "score_Prerequisite"])
    name = dict(zip(concepts.concept_id, concepts.concept_name))
    pair["source_name"] = pair.source_id.map(name); pair["target_name"] = pair.target_id.map(name)
    for c in REL_COLS[1:]:
        pair[f"score_{c}"] = 0.0

    # Prerequisite edges: each concept keeps its best related predecessors
    G = nx.DiGraph()
    for j, v in enumerate(ids):
        cand = [(score[i, j], i) for i in range(n) if i != j and related[i, j] and score[i, j] > min_score]
        for s, i in sorted(cand, reverse=True)[:top_k]:
            G.add_edge(ids[i], v, score=float(s))
    while not nx.is_directed_acyclic_graph(G):  # ties can in principle form cycles; drop weakest edge of each
        cyc = nx.find_cycle(G)
        G.remove_edge(*min(cyc, key=lambda e: G.edges[e]["score"]))

    edges = {(u, v): ("Prerequisite", d["score"], "hybrid") for u, v, d in G.edges(data=True)}
    pre_pairs = {frozenset(k) for k in edges}
    kept_llm = 0
    llm_rel_path = run_dir / "relations.csv"
    if llm_rel_path.exists():
        lr = pd.read_csv(llm_rel_path, dtype=str, keep_default_na=False)
        for s, t, rt, w in zip(lr.source_id, lr.target_id, lr.relation_type, pd.to_numeric(lr.weight)):
            if rt != "Prerequisite" and frozenset((s, t)) not in pre_pairs and (s, t) not in edges:
                edges[(s, t)] = (rt, float(w), "llm_score")
                kept_llm += 1

    ev = {}
    for (u, v) in edges:
        shared = sorted(sets[u] & sets[v])
        ev[(u, v)] = sents[shared[0]] if shared else ""
    concept_by_id = concepts.set_index("concept_id")
    rel_rows = []
    for k, ((u, v), (rt, w, src)) in enumerate(sorted(edges.items(), key=lambda e: (e[1][0], -e[1][1])), 1):
        rel_rows.append({"relation_id": f"R{k:04d}", "source_id": u, "target_id": v, "relation_type": rt,
                         "weight": round(w, 4), "page": concept_by_id.loc[u, "page"],
                         "chunk_id": concept_by_id.loc[u, "chunk_id"], "evidence": ev[(u, v)],
                         "weight_source": src, "cooccurrence_count": int(cooc[ids.index(u), ids.index(v)]),
                         "semantic_similarity": "", "chapter_proximity": "", "educational_context": ""})
    out.mkdir(parents=True, exist_ok=True)
    concepts.to_csv(out / "concepts.csv", index=False)
    pd.DataFrame(rel_rows).to_csv(out / "relations.csv", index=False)
    pair.to_csv(out / "pair_scores.csv", index=False)
    meta = {"source_run": str(run_dir), "uses_book_order": True, "signals": list(signals), "top_k": top_k,
            "prerequisite_edges": G.number_of_edges(), "llm_edges_kept": kept_llm,
            "total_edges": len(rel_rows), "concepts": n}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--top-k", type=int, default=3)
    a = ap.parse_args()
    print(json.dumps(build(a.run, a.source, a.out, a.top_k), indent=2))


if __name__ == "__main__":
    main()
