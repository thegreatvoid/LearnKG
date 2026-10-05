"""
Query-intent classification: NORMAL_QUERY vs COMPARISON_QUERY.

Pattern-based (not keyword-only): each pattern captures the two concept
*phrases* being compared, which are then resolved against the existing
domain KG by the existing `match_concept` — this module never invents or
hardcodes concept names, it only recognizes comparison *phrasing* and
hands the extracted phrases off to the real matcher.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

_COMPARISON_PATTERNS: List[re.Pattern] = [
    re.compile(r"difference(?:s)?\s+between\s+(.+?)\s+and\s+(.+?)[\?\.]?$", re.I),
    re.compile(r"similarit(?:y|ies)\s+(?:and|&)\s+difference(?:s)?\s+between\s+(.+?)\s+and\s+(.+?)[\?\.]?$", re.I),
    re.compile(r"compare\s+(.+?)\s+(?:and|with|to)\s+(.+?)[\?\.]?$", re.I),
    re.compile(r"how\s+is\s+(.+?)\s+different\s+from\s+(.+?)[\?\.]?$", re.I),
    re.compile(r"how\s+does\s+(.+?)\s+differ\s+from\s+(.+?)[\?\.]?$", re.I),
    re.compile(r"(.+?)\s+compared\s+to\s+(.+?)[\?\.]?$", re.I),
    re.compile(r"^(.+?)\s+vs\.?\s+(.+?)[\?\.]?$", re.I),
    re.compile(r"^(.+?)\s+versus\s+(.+?)[\?\.]?$", re.I),
]

_MIN_PHRASE_LEN = 2  # a matched phrase shorter than this is noise, not a concept


@dataclass
class QueryIntent:
    query_type: str  # "normal" | "comparison"
    phrase_a: Optional[str] = None
    phrase_b: Optional[str] = None


def classify_query(question: str) -> QueryIntent:
    q = question.strip()
    for pattern in _COMPARISON_PATTERNS:
        m = pattern.search(q)
        if not m:
            continue
        phrase_a, phrase_b = m.group(1).strip(" ?.,"), m.group(2).strip(" ?.,")
        if len(phrase_a) >= _MIN_PHRASE_LEN and len(phrase_b) >= _MIN_PHRASE_LEN:
            return QueryIntent(query_type="comparison", phrase_a=phrase_a, phrase_b=phrase_b)
    return QueryIntent(query_type="normal")
