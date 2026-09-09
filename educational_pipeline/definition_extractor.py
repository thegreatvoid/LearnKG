"""
Step 6: Definition Extraction
Identifies the best textbook-supported definition for each normalized concept.
Ensures definitions are grounded in the source text rather than freely hallucinated.
Preserves the exact source sentence as evidence.
"""

import re
from typing import Optional, Tuple


DEFINITION_PATTERNS = [
    # "X is defined as Y"
    re.compile(r"\b(?P<concept>[A-Z][\w\s\-]{2,30}?)\s+(?:is|are)\s+defined\s+as\s+(?P<def>[^.?!;]{15,200}[.?!])", re.IGNORECASE),
    # "X refers to Y"
    re.compile(r"\b(?P<concept>[A-Z][\w\s\-]{2,30}?)\s+refers\s+to\s+(?P<def>[^.?!;]{15,200}[.?!])", re.IGNORECASE),
    # "X is a/an Y that/which Z"
    re.compile(r"\b(?P<concept>[A-Z][\w\s\-]{2,30}?)\s+(?:is|are)\s+(?:an?|the)\s+(?P<def>[\w\s\-]+?\s+(?:that|which|used\s+to|designed\s+to|responsible\s+for)[^.?!;]{15,200}[.?!])", re.IGNORECASE),
    # "Definition: X is Y"
    re.compile(r"Definition(?:\s*\d+(?:\.\d+)*)?\s*[:\.-]\s*(?P<concept>[\w\s\-]{2,30}?)\s*(?:is|:|\-)\s*(?P<def>[^.?!;]{15,200}[.?!])", re.IGNORECASE),
]


def extract_grounded_definition(concept_name: str, text: str) -> Optional[Tuple[str, str]]:
    """
    Finds a textbook-grounded definition for the given concept within the text.
    Returns (definition, evidence_sentence) or None.
    """
    sentences = re.split(r"(?<=[.?!])\s+", text)
    escaped_concept = re.escape(concept_name)

    # 1. Search for explicit definitional sentence structures containing the concept
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue

        # Pattern: "[Concept] is a/an ...", "[Concept] refers to ...", "[Concept] is defined as ..."
        m = re.search(
            rf"\b{escaped_concept}\b\s+(?:is|are|refers\s+to|is\s+defined\s+as)\s+(?:an?|the)?\s*([^.?!;]+)",
            s_clean,
            re.IGNORECASE,
        )
        if m:
            predicate = m.group(1).strip()
            if len(predicate) > 15:
                definition = f"{concept_name} is {predicate.rstrip('.')}"
                return definition, s_clean

    # 2. Check if text starts with "[Concept]: <definition>"
    m_col = re.match(rf"^{escaped_concept}\s*[:\-]\s*([^.?!]+[.?!])", text, re.IGNORECASE)
    if m_col:
        def_text = m_col.group(1).strip()
        return def_text, f"{concept_name}: {def_text}"

    # 3. Fallback: Return the most informative sentence containing the concept as grounding evidence
    for s in sentences:
        s_clean = s.strip()
        if re.search(rf"\b{escaped_concept}\b", s_clean, re.IGNORECASE):
            if 30 <= len(s_clean) <= 250:
                return s_clean, s_clean

    return None
