"""
Step 4: Concept Extraction
Hybrid approach:
  - Extracts candidate educational concepts using deterministic NLP rules,
    capitalization cues, acronym detection, and textbook patterns.
  - Refines and enriches with LLM when available.
  - Classifies concepts into: Algorithm, Model, Formula, Theory, Component.
"""

import re
from collections import Counter
from typing import Dict, List, Set
from .chunker import EducationalChunk

STOPWORDS = {
    "a", "an", "the", "this", "that", "these", "those", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "to", "from",
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "figure", "table", "section", "chapter", "page", "study", "analysis",
    "example", "exercise", "results", "author", "authors", "approach", "method"
}

TYPE_KEYWORDS = {
    "Algorithm": ["algorithm", "descent", "search", "sort", "optimization", "method", "procedure", "backpropagation", "adam", "rmsprop"],
    "Model": ["model", "network", "system", "architecture", "classifier", "regressor", "regression"],
    "Formula": ["formula", "equation", "loss", "metric", "function", "score", "index", "ratio", "derivative", "gradient", "sum", "error"],
    "Theory": ["theory", "theorem", "principle", "law", "hypothesis", "standard", "policy", "calculus", "learning", "classification"],
    "Component": ["layer", "node", "unit", "weight", "bias", "cadre", "worker", "division", "component", "parameter", "neuron", "rate"],
}


def infer_concept_type(concept_name: str) -> str:
    """Infers the concept_type based on suffix or keywords."""
    lowered = concept_name.lower()
    for c_type, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                return c_type
    return "Component"


# Function words that make a phrase read as a grammatical fragment rather
# than a noun-phrase concept (e.g. "of the loss", "trained by", "one of
# its") when left at the edges OR in the middle of an n-gram. Kept separate
# from STOPWORDS (used elsewhere for single-word filtering) because
# phrase-boundary filtering needs to be stricter: every word in a candidate
# phrase must clear this bar, not just the first/last word.
_PHRASE_STOPWORDS = STOPWORDS | {
    "of", "with", "by", "for", "at", "into", "onto", "upon", "than", "as", "like",
    "respect", "its", "it", "one", "every", "each", "both", "some", "any", "other",
    "same", "between", "which", "who", "whom", "whose", "he", "she", "they", "we",
    "you", "i", "them", "him", "her", "such", "per", "via", "about", "after",
    "before", "during", "while", "used", "using", "trained", "moves", "and", "or",
    "through", "within", "without", "based", "small", "large", "long", "short",
    "since", "often", "single", "practice", "computes", "passes", "means",
    "makes", "gives", "takes", "seen", "known", "given", "rather", "instead",
}


def extract_corpus_key_phrases(
    full_text: str,
    max_len: int = 3,
    min_count_phrase: int = 2,
    min_count_word: int = 4,
    min_word_len: int = 5,
) -> Set[str]:
    """
    Domain-agnostic replacement for a hand-maintained term whitelist: finds
    terms that recur across the WHOLE document (not just within one chunk),
    on the theory that a word/phrase a textbook repeats several times is a
    concept the text actually cares about, regardless of subject matter.
    This lets the pipeline surface technical terms that never get
    capitalized in prose (e.g. "loss function", "backpropagation")
    without hardcoding any per-domain vocabulary — call it once per
    document and thread the result into every chunk's extraction pass.

    Two signals, both purely frequency-based:
      - Multi-word phrases (2-`max_len` words): every word must clear
        `_PHRASE_STOPWORDS` and be >=3 chars, so grammatical fragments
        built around prepositions/pronouns ("of the loss", "trained by")
        never qualify — only genuine noun phrases do. Needs >= `min_count_phrase`
        occurrences.
      - Single words (>= `min_word_len` chars, not a stopword): a higher
        `min_count_word` threshold, since unigrams are much more likely to
        be incidental than a recurring multi-word phrase — this is how
        single-word technical terms (e.g. "backpropagation") get picked up
        even though they're too short a unit for the phrase signal above.
    """
    words = re.findall(r"[a-zA-Z]+", full_text.lower())
    counts: Counter = Counter()
    for n in range(2, max_len + 1):
        for i in range(len(words) - n + 1):
            gram = words[i : i + n]
            if any(len(w) < 3 or w in _PHRASE_STOPWORDS for w in gram):
                continue
            counts[" ".join(gram)] += 1
    multiword_terms = {phrase for phrase, count in counts.items() if count >= min_count_phrase}

    word_counts = Counter(w for w in words if len(w) >= min_word_len and w not in _PHRASE_STOPWORDS)
    single_words = {w for w, count in word_counts.items() if count >= min_count_word}

    # Drop any single word that's just a component of a phrase already
    # captured above (e.g. don't keep standalone "gradient"/"descent" once
    # "gradient descent" itself qualified) — otherwise every multi-word
    # concept spawns redundant single-word duplicates of its own pieces.
    phrase_component_words = {w for phrase in multiword_terms for w in phrase.split()}
    single_words -= phrase_component_words

    return multiword_terms | single_words


def extract_candidate_concepts_from_text(text: str, corpus_terms: Set[str] = None) -> List[str]:
    """
    Extracts candidate educational terms using multi-word noun phrase patterns,
    capitalized phrases, acronyms, and document-derived recurring phrases.
    `corpus_terms` (see `extract_corpus_key_phrases`) is computed once per
    document and passed in here — no fixed, hand-maintained domain
    vocabulary is used, so this works the same way regardless of subject
    matter.
    """
    candidates: Set[str] = set()

    # 1. Capitalized multi-word terms on same line (2 to 4 words, e.g. "Gradient Descent")
    cap_phrase = re.findall(r"\b([A-Z][a-z]+(?:[^\S\r\n]+[A-Z][a-z]+){1,3})\b", text)
    for p in cap_phrase:
        p_clean = p.strip()
        first_word = p_clean.split()[0].lower()
        if first_word not in STOPWORDS and len(p_clean) > 3:
            candidates.add(p_clean)

    # 2. All-caps Acronyms and camelCase terms (e.g., "WHO", "IPHS", "NMC", "GD", "RMSProp", "Adam")
    acronyms = re.findall(r"\b(?:[A-Z]{2,6}|RMSProp|Adam)\b", text)
    for acr in acronyms:
        if acr.lower() not in STOPWORDS and acr not in {"AND", "THE", "FOR", "NOT"}:
            candidates.add(acr)

    # 3. Quoted or italicized concepts ("...", '...')
    quoted = re.findall(r"[\"']([A-Za-z0-9\s\-]{3,30})[\"']", text)
    for q in quoted:
        q_clean = q.strip()
        if len(q_clean.split()) <= 4 and q_clean.lower() not in STOPWORDS:
            candidates.add(q_clean.title())

    # 4. Keywords: definition/concept indicators
    def_matches = re.findall(r"(?:defined\s+as|known\s+as|termed|called|referred\s+to\s+as)\s+(?:an?|the)?\s*([A-Za-z0-9\s\-]{3,30})", text, re.IGNORECASE)
    for d in def_matches:
        d_clean = d.strip()
        if len(d_clean.split()) <= 3 and d_clean.lower() not in STOPWORDS:
            candidates.add(d_clean.title())

    # 5. Recurring multi-word phrases from this same document (corpus-driven,
    # not a hardcoded domain list — see extract_corpus_key_phrases) that
    # also happen to appear in this specific chunk.
    if corpus_terms:
        for term in corpus_terms:
            if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
                candidates.add(term.title())

    return list(candidates)


def extract_concepts_for_chunk(
    chunk: EducationalChunk, llm_concepts: List[dict] = None, corpus_terms: Set[str] = None
) -> List[dict]:
    """
    Combines rule-based candidates with LLM-extracted concepts.
    Returns list of concept dicts: {concept_name, aliases, concept_type, definition, evidence}
    """
    results: Dict[str, dict] = {}

    # If LLM extracted concepts are provided
    if llm_concepts:
        for c in llm_concepts:
            name = str(c.get("concept_name", "")).strip()
            if name:
                results[name.lower()] = {
                    "concept_name": name,
                    "aliases": c.get("aliases", []),
                    "concept_type": c.get("concept_type", infer_concept_type(name)),
                    "definition": c.get("definition", ""),
                    "evidence": c.get("evidence", ""),
                }

    # Supplement with deterministic candidates
    candidates = extract_candidate_concepts_from_text(chunk.text, corpus_terms=corpus_terms)
    for cand in candidates:
        cand_lower = cand.lower()
        if cand_lower not in results:
            results[cand_lower] = {
                "concept_name": cand,
                "aliases": [],
                "concept_type": infer_concept_type(cand),
                "definition": "",
                "evidence": "",
            }

    return list(results.values())
