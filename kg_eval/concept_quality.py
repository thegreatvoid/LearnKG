"""Concept-extraction quality (no humans; an LLM only for the optional precision judge).

  python -m kg_eval.concept_quality --kg-dir data_output/ck12_geometry_kgx_cand
  python -m kg_eval.concept_quality --kg-dir ... --judge-model llama3.1:8b --subject geometry   # + precision

Reports: concepts found verbatim in the textbook (hallucination = 1 - rate); recall of AL-CPL gold concepts
(a matching KG concept exists; high-confidence matches reported separately); and, if candidate_pairs.csv or
pair_scores.csv exists, how many gold positive pairs the pair generator even considered (an upper bound on recall).

Recall alone rewards keeping everything, so noise ("times", "states") is invisible to it. With --judge-model an
LLM labels every concept, given its evidence sentence, as concept / not_concept / duplicate; precision is the
share labelled concept. Use a different model from the one that extracted the concepts, or the judge grades its
own output. Verdicts are cached in <out>/concept_judge_cache.jsonl, keyed by model, subject and concept name.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from evaluate_prerequisite_extraction import build_extracted_concept_index, match_gold_concept
from .data import DEFAULT_KG_DIR, DEFAULT_SOURCE, fmt, load_alcpl, load_kg, read_source


def _norm(s):
    import re
    return " " + " ".join(re.findall(r"[a-z0-9]+", str(s).lower())) + " "


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"judgments": {"type": "array", "items": {
        "type": "object",
        "properties": {"name": {"type": "string"},
                       "verdict": {"type": "string", "enum": ["concept", "not_concept", "duplicate"]},
                       "same_as": {"type": "string"}},
        "required": ["name", "verdict", "same_as"], "additionalProperties": False}}},
    "required": ["judgments"], "additionalProperties": False,
}
JUDGE_SYSTEM = (
    "You audit the concept list of an educational knowledge graph for {subject}. For each term, judge from the term "
    "and its evidence sentence:\n"
    "- concept: a technical concept, object, property, theorem or method that a student of {subject} must learn.\n"
    "- not_concept: an ordinary word or phrase, an arithmetic expression, a sentence fragment, a label such as a "
    "point name, a section or chapter title, a tool, or a mnemonic.\n"
    "- duplicate: the same concept as another term in this list (singular/plural, abbreviation, longer name); "
    "put that other term in same_as.\n"
    "Return one judgment per term, with the term exactly as given. same_as is an empty string unless duplicate."
)


def judge_concepts(concepts: pd.DataFrame, backend, subject: str, cache_path: Path, batch: int = 25) -> List[Dict]:
    """One {name, verdict, same_as} per concept; verdict "unjudged" if the model skipped it or every call failed."""
    cache: Dict[str, Dict] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r["key"]] = r

    def key(name):
        return f"{backend.model}|{subject}|{str(name).lower()}"

    evidence = concepts["evidence"] if "evidence" in concepts else [""] * len(concepts)
    definition = concepts["definition"] if "definition" in concepts else [""] * len(concepts)
    rows = [(str(n), str(e if isinstance(e, str) and e else d if isinstance(d, str) else ""))
            for n, e, d in zip(concepts["concept_name"], evidence, definition)]
    todo = [r for r in rows if key(r[0]) not in cache]
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        listing = "\n".join(f"- {n} | evidence: {e[:200]}" for n, e in part)
        try:
            res = backend.chat_json(JUDGE_SYSTEM.format(subject=subject), f"Terms:\n{listing}", JUDGE_SCHEMA)
        except RuntimeError:
            continue  # the backend counts the failure; these concepts stay unjudged
        names = {n.lower() for n, _ in part}
        with cache_path.open("a", encoding="utf-8") as f:
            for j in res.get("judgments", []):
                n = str(j.get("name", "")).strip()
                if n.lower() in names and key(n) not in cache:
                    rec = {"key": key(n), "verdict": j.get("verdict", ""), "same_as": j.get("same_as", "")}
                    cache[rec["key"]] = rec
                    f.write(json.dumps(rec) + "\n")
    return [{"name": n, "verdict": cache.get(key(n), {}).get("verdict", "unjudged"),
             "same_as": cache.get(key(n), {}).get("same_as", "")} for n, _ in rows]


def precision_report(judged: List[Dict]) -> Dict:
    done = [j for j in judged if j["verdict"] in ("concept", "not_concept", "duplicate")]
    names = lambda v: [j["name"] for j in done if j["verdict"] == v]
    rate = lambda v: len(names(v)) / len(done) if done else None
    return {"judged": len(done), "unjudged": len(judged) - len(done),
            "concept_precision": rate("concept"), "not_concept_rate": rate("not_concept"),
            "duplicate_rate": rate("duplicate"), "not_concept": sorted(names("not_concept")),
            "duplicates": sorted(f"{j['name']} = {j['same_as']}" for j in done if j["verdict"] == "duplicate")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kg-dir", type=Path, default=DEFAULT_KG_DIR)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--judge-model", default=None,
                    help="Ollama model for the concept-precision judge (off if omitted; use a model other than the extractor's)")
    ap.add_argument("--subject", default="the subject of this textbook", help="subject named in the judge prompt")
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
    if a.judge_model:
        from kg_extract.backend import OllamaBackend
        backend = OllamaBackend(a.judge_model)
        judged = judge_concepts(concepts, backend, a.subject, out / "concept_judge_cache.jsonl")
        pd.DataFrame(judged).to_csv(out / "concept_judgments.csv", index=False)
        rep["precision"] = {"judge_model": a.judge_model, "subject": a.subject, **precision_report(judged),
                            "backend_counters": dict(backend.counters)}
    (out / "concept_quality_report.json").write_text(json.dumps(rep, indent=2, default=str))
    print(f"concepts={rep['n_concepts']}  verbatim in text={fmt(rep['verbatim_in_text_rate'])}")
    print(f"AL-CPL concept recall: any={fmt(rep['gold_concept_recall_any'])}  high-confidence={fmt(rep['gold_concept_recall_high_confidence'])}"
          f" ({len(matched)}/{len(names)})")
    if "candidate_recall_upper_bound" in rep:
        print(f"gold positive pairs considered by pair generator: {rep['gold_positive_pairs_considered_by_generator']}/"
              f"{rep['gold_positive_pairs_with_both_concepts']} = {fmt(rep['candidate_recall_upper_bound'])}")
    print("missing gold concepts:", rep["gold_concepts_missing"][:20])
    if "precision" in rep:
        pr = rep["precision"]
        print(f"concept precision ({pr['judge_model']}): {fmt(pr['concept_precision'])}  "
              f"not_concept={fmt(pr['not_concept_rate'])}  duplicate={fmt(pr['duplicate_rate'])}  "
              f"judged={pr['judged']} unjudged={pr['unjudged']}")
        print("not concepts:", pr["not_concept"][:30])


if __name__ == "__main__":
    main()
