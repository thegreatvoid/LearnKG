"""Stages 1-2: grounded concept candidates, consolidation, salience ranking. No domain vocabulary."""

import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

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
    # "X is a/the ...": group 2 is the word after the article, used to reject non-concepts ("SOH CAH TOA is the mnemonic").
    # The article needs a following space, or "Angles are called ..." yields "gles".
    re.compile(r"(?:^|[.!?]\s+|\n)(?:(?:An?|The)\s+)?([A-Za-z][A-Za-z\- ]{2,40}?)\s+(?:is|are)\s+(?:an?|the|defined as)\s+([A-Za-z]+)"),
    # "called X": the term ends at punctuation or at the next function word/verb, not at the first space
    # (otherwise "called remote interior angles" yields "remote").
    re.compile(r"\b(?:called|known as|termed|referred to as|define[sd]? as)\s+(?:an?|the)?\s*([A-Za-z][A-Za-z\- ]{2,40}?)"
               r"(?=\s*[,.;:)]|\s+(?:is|are|was|were|and|or|that|which|because|if|when|where|of|in|to|with|for)\b|\s*$)", re.M),
    # "A ray is part of ...", "A kite has ...": a sentence opening with an indefinite subject introduces that thing.
    re.compile(r"(?:^|[.!?]\s+|\n)An?\s+([A-Za-z][A-Za-z\- ]{2,40}?)\s+(?:is|are|has|have|consists)\s+(?:(?:an?|the)\s+)?([A-Za-z]+)"),
]
# "X is a mnemonic/abbreviation/tool ...", "X is used to ...": a memory aid or an instrument, not a concept.
_NON_CONCEPT_PREDICATES = {"mnemonic", "acronym", "abbreviation", "nickname", "tool", "instrument", "device", "used"}
_HEADING_NUM = re.compile(r"^\s*(?:chapter\s+)?[\d.]+\s*[:.\-]?\s*", re.I)
# Heading words that relate the topic to something else: "Properties of Parallel Lines", "Proofs about Segments".
_HEADING_PREP = re.compile(r"\s+(?:of|about|in|from|using|by|for|with|are|is)\s+", re.I)
_GERUND = re.compile(r"^[A-Za-z]{3,}ing\s+(?=\S)")  # "Classifying Triangles", "Exploring Symmetry"
# Arithmetic operator words: a noun chunk containing one is an expression ("pi times radius", "one half base").
_ARITHMETIC = {"times", "plus", "minus", "half", "halves", "third", "thirds", "twice", "quarter", "divided", "squared",
               "cubed"}

# Domain specificity of noun-chunk-only candidates, from general-English word frequency (Zipf scale: 3.5 is about
# once per 30k words, 4.5 about once per 3k). Fixed a priori, not tuned on gold labels.
try:
    from wordfreq import zipf_frequency
except ImportError:  # optional: without it the rarity rescue and the common-phrase rule are skipped
    # (counter "wordfreq_unavailable" in run_meta.json)
    zipf_frequency = None
RARE_ZIPF = 3.5    # a lone noun rarer than this is a domain term ("hypotenuse"), even without a definition cue
COMMON_ZIPF = 4.5  # a phrase made only of words commoner than this is ordinary English ("specific examples")


def rarest_word_zipf(term: str) -> Optional[float]:
    """General-English Zipf frequency of the term's rarest word (None if wordfreq is not installed)."""
    if zipf_frequency is None:
        return None
    return min(zipf_frequency(w, "en") for w in re.findall(r"[A-Za-z]+", term))


def heading_terms(heading: str) -> List[Tuple[str, str]]:
    """(term, cue) pairs from a section heading. The topic noun gets cue "heading"; a generic leading part of
    "X of/about/using Y" ("Properties", "Proofs") only gets the weak cue "heading_part"."""
    h = _HEADING_NUM.sub("", heading or "").strip(" :.-")
    parts = [p.strip() for p in re.split(r"\band\b|,|:", h) if p.strip()]
    parts = [_GERUND.sub("", p) for p in parts]
    # Coordinated modifiers share the head noun: "Isosceles and Equilateral Triangles" -> "Isosceles Triangles".
    if len(parts) > 1 and len(parts[-1].split()) > 1:
        head = parts[-1].split()[-1]
        parts = [p + " " + head if len(p.split()) == 1 else p for p in parts[:-1]] + [parts[-1]]
    out = []
    for p in parts:
        pieces = [x.strip() for x in _HEADING_PREP.split(p) if x.strip()]
        for i, x in enumerate(pieces):
            if 1 <= len(x.split()) <= 4:
                out.append((x, "heading_part" if i < len(pieces) - 1 else "heading"))
    return out


def clean_term(t: str) -> Optional[str]:
    t = re.sub(r"\s+", " ", t).strip(" \t\n.,;:()[]\"'")
    t = re.sub(r"^(?:an?|the|this|that|these|those|its|their|our|each|any|every|some)\s+", "", t, flags=re.I)
    w = t.split()
    if not (1 <= len(w) <= 4) or t.lower() in GENERIC:
        return None
    is_acronym = bool(re.fullmatch(r"[A-Z]{2,4}", t))
    if not is_acronym:
        if len(t) < 3 or not re.search(r"[A-Za-z]{3,}", t):
            return None
    if all(x.lower() in GENERIC for x in w):
        return None
    return t


def _keep_token(t, i: int) -> bool:
    """Whether noun-chunk token t (position i in the chunk) belongs in the term name."""
    if t.is_space or t.pos_ in ("PRON", "DET"):
        return False
    doc = t.doc
    # Numbers and hyphens survive only inside a hyphenated word: "two-column proof", not "3 sides".
    if t.text == "-":
        return t.i > 0 and t.i + 1 < len(doc) and not doc[t.i - 1].whitespace_ and not t.whitespace_
    if t.like_num:
        return t.i + 1 < len(doc) and doc[t.i + 1].text == "-" and not t.whitespace_
    if t.is_stop or t.is_punct:
        return False
    # Point/variable labels after a noun ("angle ABC", "segment AB", "n sides"), but not leading codes like "SSS".
    after_noun = any(p.pos_ in ("NOUN", "PROPN") and not p.text.isupper() for p in doc[t.i - i:t.i])
    if (after_noun and re.fullmatch(r"[A-Z]{1,3}", t.text)) or re.fullmatch(r"[a-z]", t.text):
        return False
    return True


def spacy_noun_chunks(text: str, nlp) -> List[str]:
    out = []
    # One line at a time: headings sit on their own line and must not merge with the next sentence.
    for line in text.splitlines():
        doc = nlp(line)
        for nc in doc.noun_chunks:
            if any(t.lower_ in _ARITHMETIC for t in nc):
                continue
            toks = [t for i, t in enumerate(nc) if _keep_token(t, i)]
            # spaCy often tags a verb right after the subject as a noun: "The hinge theorem states that ...",
            # "Right angles measure 90", "The contrapositive negates both". A following "that" + clause subject
            # (not "angles that are ..."), or a following number/determiner, marks the last word as that verb.
            nxt = doc[nc.end:nc.end + 2]
            if len(toks) > 1 and toks[-1].tag_ in ("NN", "NNS", "VBZ", "VBP") and len(nxt) > 0 and (
                    (nxt[0].lower_ == "that" and len(nxt) == 2 and nxt[1].pos_ not in ("VERB", "AUX"))
                    or nxt[0].pos_ in ("NUM", "DET", "PRON")):
                toks = toks[:-1]
            if toks and toks[-1].tag_ == "VBG":  # "faces meeting"
                toks = toks[:-1]
            if toks and toks[-1].pos_ in ("NOUN", "PROPN"):
                c = clean_term(" ".join(t.text for t in toks).replace(" - ", "-"))
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

    # Section headings only: chapter titles name broad topics ("Relationships with Triangles"), not concepts.
    for t, cue in heading_terms(chunk.section):
        add(t, cue)
    for pat in _DEF_PATTERNS:
        for m in pat.finditer(chunk.text):
            if m.lastindex == 2 and m.group(2).lower() in _NON_CONCEPT_PREDICATES:
                continue
            add(m.group(1), "definition")
    if nlp is not None:
        for t in spacy_noun_chunks(chunk.text, nlp):
            add(t, "np")
    return c


def extract_concepts(chunks, backend: Optional[OllamaBackend], full_text: str, top_k: int = 150, min_freq: int = 1,
                     nlp=None, ground: bool = True, counters: Optional[Counter] = None):
    """Returns (normalizer, report). `ground=False` is an ablation switch only. report["candidates"] lists every
    pooled candidate with its cues, salience and why it was dropped (if it was)."""
    counters = counters if counters is not None else Counter()
    index = TextIndex(full_text)
    # Frequency and the heading check use the text without heading lines, so a heading's own words don't count.
    headings = {h.strip() for ch in chunks for h in (ch.chapter, ch.section) if h and h.strip()}
    body = TextIndex("\n".join(l for l in full_text.splitlines() if l.strip() not in headings))
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

    # Salience: heading/definition/LLM cues, frequency in the book body.
    if zipf_frequency is None:
        counters["wordfreq_unavailable"] = 1
    scored, rows = [], {}
    for key, e in pooled.items():
        freq = body.count(e["name"])
        s = 3 * ("heading" in e["cues"]) + 2 * ("definition" in e["cues"]) + 2 * ("llm" in e["cues"]) \
            + 0.5 * ("np" in e["cues"]) + math.log1p(freq)
        weak = e["cues"] <= {"np", "heading_part"}  # no definition, section-heading or LLM cue
        zipf = rarest_word_zipf(e["name"])
        rows[key] = {"name": e["name"], "cues": "+".join(sorted(e["cues"])), "freq": freq, "salience": round(s, 3),
                     "general_zipf": None if zipf is None else round(zipf, 2), "dropped": ""}
        drop = ""
        if freq < min_freq and "heading" not in e["cues"] and "definition" not in e["cues"]:
            drop = "min_freq"
        elif weak and len(e["name"].split()) == 1:
            # Frequent domain terms (freq >= 3) are preserved; lone noun-chunk acronyms are point labels
            is_acronym = bool(re.fullmatch(r"[A-Z]{2,4}", e["name"]))
            if is_acronym:
                drop = "weak_single_word"
            elif freq < 3 and (zipf is None or zipf >= RARE_ZIPF):
                drop = "weak_single_word"
        elif weak and zipf is not None and zipf >= COMMON_ZIPF:
            drop = "weak_common_phrase"
        if drop:
            rows[key]["dropped"] = drop
            counters[f"candidates_dropped_{drop}"] += 1
            continue
        # Ties (common among once-mentioned noun chunks) go to the more domain-specific term, then by name.
        scored.append((-s, zipf if zipf is not None else 99.0, e["name"].lower(), key))
    scored.sort()
    keep = [k for *_, k in scored[:top_k]]
    for *_, k in scored[top_k:]:
        rows[k]["dropped"] = "top_k"

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
    return normalizer, {"scored": len(scored), "kept": len(keep),
                        "candidates": sorted(rows.values(), key=lambda r: -r["salience"])}
