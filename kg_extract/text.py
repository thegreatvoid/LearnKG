"""Text normalisation shared by grounding, candidate generation and pair generation."""

import re
from typing import Iterable, List, Set


def stem_token(t: str) -> str:
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("es") and t[-3] in "sxz":
        return t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def stems(text: str) -> List[str]:
    return [stem_token(t) for t in re.findall(r"[a-z0-9]+", text.lower())]


def norm(text: str) -> str:
    """Lower-cased, punctuation-free, crudely singularised, space-padded for whole-phrase containment checks."""
    return " " + " ".join(stems(text)) + " "


class TextIndex:
    """Phrase containment/count over a body of text (the grounding test)."""

    def __init__(self, text: str):
        self.text = norm(text)

    def count(self, phrase: str) -> int:
        p = norm(phrase)
        return self.text.count(p) if p.strip() else 0

    def contains(self, phrase: str) -> bool:
        return self.count(phrase) > 0


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 3]


def mentions(sentence_norm: str, names: Iterable[str]) -> bool:
    return any(norm(n) in sentence_norm for n in names if n.strip())
