"""Stages 1-2: grounded concept candidates, consolidation, salience ranking. No domain vocabulary."""

import math
import re
from collections import Counter
from typing import Dict, List, Optional

from educational_pipeline.definition_extractor import extract_grounded_definition
from educational_pipeline.normalizer import ConceptNormalizer

from .backend import BackendError, OllamaBackend
from .text import TextIndex, norm, split_sentences

GENERIC = {
    "example", "exercise", "figure", "table", "chapter", "section", "problem", "answer", "review", "summary",
    "lesson", "page", "result", "question", "way", "number", "thing", "following", "case", "use", "form",
    "time", "part", "type", "set", "line segment of", "it", "this", "that", "they", "we", "you", "i",
}

CONCEPT_SCHEMA = {
    "type": "object",
    "properties": {"concepts": {"type": "array", "items": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "definition_sentence": {"type": "string"}},
        "required": ["name", "definition_sentence"], "additionalProperties": False}}},
    "required": ["concepts"], "additionalProperties": False,
}
CONCEPT_SYSTEM = (
    "You extract the key technical terms that a textbook passage DEFINES or INTRODUCES for the first time. "
    "Return only terms that appear in the passage verbatim (same wording), 1-4 words, singular, no examples, "
    "numbers, people or section titles like 'Example 1'. For each, copy the sentence from the passage that "
    "defines or introduces it. If the passage introduces no technical term return an empty list."
)

_DEF_PATTERNS = [
    re.compile(r"(?:^|[.!?]\s+|\n)(?:An?|The)?\s*([A-Za-z][A-Za-z\- ]{2,40}?)\s+(?:is|are)\s+(?:an?|the|defined as|called)\b"),
    re.compile(r"\b(?:called|known as|termed|referred to as|define[sd]? as)\s+(?:an?|the)?\s*([A-Za-z][A-Za-z\- ]{2,40}?)(?=[\s,.;:)])"),
]
_HEADING_NUM = re.compile(r"^\s*(?:chapter\s+)?[\d.]+\s*[:.\-]?\s*", re.I)


def heading_terms(heading: str) -> List[str]:
    h = _HEADING_NUM.sub("", heading or "").strip(" :.-")
    parts = [p.strip() for p in re.split(r"\band\b|,|:", h) if p.strip()]
    return [p for p in parts if 1 <= len(p.split()) <= 4]


def clean_term(t: str) -> Optional[str]:
    t = re.sub(r"\s+", " ", t).strip(" \t\n.,;:()[]\"'")
    t = re.sub(r"^(?:an?|the|this|that|these|those|its|their|our|each|any|every|some)\s+", "", t, flags=re.I)
    w = t.split()
    if not (1 <= len(w) <= 4) or len(t) < 3 or t.lower() in GENERIC or not re.search(r"[A-Za-z]{3,}", t):
        return None
    if all(x.lower() in GENERIC for x in w):
        return None
    return t


def spacy_noun_chunks(text: str, nlp) -> List[str]:
    out = []
    for nc in nlp(text).noun_chunks:
        toks = [t for t in nc if not (t.is_stop or t.is_punct or t.like_num or t.pos_ in ("PRON", "DET"))]
        if toks and toks[-1].pos_ in ("NOUN", "PROPN"):
            c = clean_term(" ".join(t.text for t in toks))
            if c:
                out.append(c)
    return out


def rule_candidates(chunk, nlp=None) -> Dict[str, dict]:
    """Domain-agnostic candidates from one chunk, with the cue that produced each."""
    c: Dict[str, dict] = {}

    def add(term, cue):
        t = clean_term(term)
        if t:
            c.setdefault(t.lower(), {"name": t, "cues": set()})["cues"].add(cue)

    for h in (chunk.section, chunk.chapter):
        for t in heading_terms(h):
            add(t, "heading")
    for pat in _DEF_PATTERNS:
        for m in pat.finditer(chunk.text):
            add(m.group(1), "definition")
    if nlp is not None:
        for t in spacy_noun_chunks(chunk.text, nlp):
            add(t, "np")
    return c


def extract_concepts(chunks, backend: Optional[OllamaBackend], full_text: str, top_k: int = 150, min_freq: int = 1,
                     nlp=None, ground: bool = True, counters: Optional[Counter] = None):
    """Returns (normalizer, report). `ground=False` is an ablation switch only."""
    counters = counters if counters is not None else Counter()
    index = TextIndex(full_text)
    pooled: Dict[str, dict] = {}

    def pool(name, cue, chunk, definition=""):
        t = clean_term(name)
        if not t:
            return
        counters["candidates_seen"] += 1
        if ground and not index.contains(t):
            counters["candidates_dropped_ungrounded"] += 1
            return
        e = pooled.setdefault(t.lower(), {"name": t, "cues": set(), "chunk": chunk, "definition": ""})
        e["cues"].add(cue)
        if cue == "llm":
            e["chunk"], e["definition"] = chunk, definition or e["definition"]

    for ch in chunks:
        for e in rule_candidates(ch, nlp).values():
            for cue in e["cues"]:
                pool(e["name"], cue, ch)
        if backend is not None:
            try:
                res = backend.chat_json(CONCEPT_SYSTEM, f"Passage:\n{ch.text}", CONCEPT_SCHEMA)
            except BackendError:
                counters["chunks_llm_failed"] += 1
                continue
            counters["chunks_llm_ok"] += 1
            for item in res.get("concepts", []):
                sent = item.get("definition_sentence", "")
                pool(item.get("name", ""), "llm", ch, sent if sent and norm(sent) in norm(ch.text) else "")

    # Salience: heading/definition/LLM cues, frequency in the whole book.
    scored = []
    for key, e in pooled.items():
        freq = index.count(e["name"])
        if freq < min_freq:
            continue
        s = 3 * ("heading" in e["cues"]) + 2 * ("definition" in e["cues"]) + 2 * ("llm" in e["cues"]) \
            + 0.5 * ("np" in e["cues"]) + math.log1p(freq)
        scored.append((s, key))
    scored.sort(reverse=True)
    keep = [k for _, k in scored[:top_k]]

    normalizer = ConceptNormalizer()
    for key in sorted(keep, key=lambda k: pooled[k]["name"].lower()):  # deterministic IDs
        e = pooled[key]
        ch = e["chunk"]
        definition, evidence = e["definition"], e["definition"]
        if not definition:
            g = extract_grounded_definition(e["name"], ch.text)
            if g:
                definition, evidence = g
        normalizer.register_concept(
            name=e["name"], concept_type="Concept", definition=definition, chapter=ch.chapter,
            section=ch.section, page=ch.page, chunk_id=ch.chunk_id, evidence=evidence)
    counters["concepts_kept"] = len(normalizer.concepts_by_id)
    return normalizer, {"scored": len(scored), "kept": len(keep)}
