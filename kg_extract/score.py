"""Stage 4: LLM pair scoring. Every candidate pair gets a direction-specific score per relation type."""

from collections import Counter, defaultdict
from typing import Dict, List, Optional

from .backend import BackendError, OllamaBackend

RELATIONS = ["Prerequisite", "Part-of", "Application", "Extension", "Similarity"]

PAIR_SCHEMA = {
    "type": "object",
    "properties": {
        "relation": {"type": "string", "enum": RELATIONS + ["None"]},
        "source": {"type": "string", "enum": ["A", "B", "none"]},
        "confidence": {"type": "number"},
    },
    "required": ["relation", "source", "confidence"], "additionalProperties": False,
}
PAIR_SYSTEM = (
    "You decide how two concepts from a textbook are related, using ONLY the evidence given. "
    "Relation types (the SOURCE is the concept the arrow starts from):\n"
    "- Prerequisite: the source must be understood BEFORE the target (the target's definition or use depends on it).\n"
    "- Part-of: the source is a component or special case of the target (e.g. a radius is part of a circle).\n"
    "- Application: the source is applied or used inside the target.\n"
    "- Extension: the source builds upon / generalises the target (the target comes first).\n"
    "- Similarity: the two are alike or contrasted; no direction (answer source A).\n"
    "- None: the evidence does not support any of these. Prefer None over guessing.\n"
    "Return the relation, which concept is the source (A, B, or none), and your confidence from 0 to 1."
)


def pair_prompt(a, b, evidence: List[str], swap: bool) -> str:
    x, y = (b, a) if swap else (a, b)
    ev = "\n".join(f"- {s}" for s in evidence[:4])
    return (f"Concept A: {x.concept_name}\nDefinition: {x.definition or '(none)'}\n\n"
            f"Concept B: {y.concept_name}\nDefinition: {y.definition or '(none)'}\n\n"
            f"Evidence from the textbook:\n{ev}\n\nHow are A and B related?")


def score_pairs(backend: OllamaBackend, normalizer, candidates, samples: int = 2, counters: Optional[Counter] = None):
    """Returns {(src_id, tgt_id): {relation: score}} plus per-pair metadata.

    Sample i uses swapped A/B order when i is odd (cancels position bias); the first two samples run at
    temperature 0, extra samples at 0.3 with distinct seeds. A sample votes `confidence` for (relation,
    direction); the score is the vote mass divided by the number of successful samples."""
    counters = counters if counters is not None else Counter()
    scores: Dict[tuple, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    meta: Dict[frozenset, dict] = {}
    for cand in candidates:
        a, b = normalizer.concepts_by_id[cand["a"]], normalizer.concepts_by_id[cand["b"]]
        votes, ok = [], 0
        for i in range(samples):
            swap = i % 2 == 1
            try:
                res = backend.chat_json(PAIR_SYSTEM, pair_prompt(a, b, cand["evidence"], swap), PAIR_SCHEMA,
                                        temperature=0.0 if i < 2 else 0.3, seed=i)
            except BackendError:
                counters["pairs_sample_failed"] += 1
                continue
            ok += 1
            rel, conf = res["relation"], max(0.0, min(1.0, float(res["confidence"])))
            if rel == "None" or res["source"] == "none":
                continue
            first, second = (b, a) if swap else (a, b)  # what the model called A and B
            src, tgt = (first, second) if res["source"] == "A" else (second, first)
            if rel == "Similarity":  # undirected: canonical order
                src, tgt = (a, b) if a.concept_id < b.concept_id else (b, a)
            votes.append((src.concept_id, tgt.concept_id, rel, conf))
        counters["pairs_scored"] += 1 if ok else 0
        if not ok:
            continue
        for s, t, rel, conf in votes:
            scores[(s, t)][rel] += conf / ok
        meta[frozenset((a.concept_id, b.concept_id))] = {"n_ok": ok, "cooc": cand["cooc"], "evidence": cand["evidence"]}
    return scores, meta
