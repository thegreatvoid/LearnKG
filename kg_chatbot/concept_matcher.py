"""
Maps a free-text user question to the most relevant concept in the domain
KG. Reuses ConceptNormalizer's name-cleaning/fuzzy-matching
(educational_pipeline/normalizer.py) instead of writing a new matcher, plus
a simple keyword-overlap score against each concept's name/aliases/
definition.
"""

import re
from dataclasses import dataclass
from typing import Optional, Set

from educational_pipeline.normalizer import ConceptNormalizer

from .kg_adapter import KGNode, KnowledgeGraph

_STOPWORDS = {
    "why", "does", "do", "is", "are", "what", "how", "the", "a", "an", "to",
    "of", "in", "on", "for", "we", "need", "use", "uses", "using", "i",
    "dont", "understand", "explain", "and", "or", "it", "this", "that",
    "about", "with", "can", "you", "me", "please",
}


def _tokenize(text: str) -> Set[str]:
    return {w for w in re.findall(r"[a-zA-Z]{2,}", text.lower()) if w not in _STOPWORDS}


@dataclass
class ConceptMatch:
    node: KGNode
    score: float
    confidence: str


def match_concept(question: str, kg: KnowledgeGraph) -> Optional[ConceptMatch]:
    """Finds the concept in `kg` most relevant to `question`."""
    cleaned_q = ConceptNormalizer.clean_name(question).lower()
    question_lower = question.lower()
    q_tokens = _tokenize(question)

    best: Optional[ConceptMatch] = None
    for node in kg.all_nodes():
        names_to_check = [node.label] + node.aliases
        name_signal = 0.0
        for name in names_to_check:
            name_l = name.lower()
            if name_l in question_lower:
                name_signal = max(name_signal, 1.0)
            elif ConceptNormalizer._is_fuzzy_match(cleaned_q, name_l):
                name_signal = max(name_signal, 0.75)

        name_tokens = _tokenize(node.label)
        token_overlap = len(q_tokens & name_tokens) / max(1, len(name_tokens))

        desc_tokens = _tokenize(node.description)
        desc_overlap = len(q_tokens & desc_tokens) / max(1, len(desc_tokens)) if desc_tokens else 0.0

        score = 0.6 * name_signal + 0.3 * token_overlap + 0.1 * desc_overlap

        if best is None or score > best.score:
            confidence = "High" if score >= 0.6 else "Medium" if score >= 0.3 else "Low"
            best = ConceptMatch(node=node, score=score, confidence=confidence)

    if best and best.score > 0.05:
        return best
    return None
