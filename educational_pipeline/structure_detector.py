"""
Step 2: Educational Structure Detection
Identifies meaningful educational blocks:
  - Chapter
  - Section
  - Definition
  - Explanation
  - Example
  - Exercise
  - Theorem
  - Proof
  - Algorithm
  - Summary
Uses rules and regex layout analysis with fallback to Explanation.
"""

import re
from dataclasses import dataclass
from typing import List
from .parser import ParsedBlock


EDUCATIONAL_TYPES = {
    "Chapter",
    "Section",
    "Definition",
    "Explanation",
    "Example",
    "Exercise",
    "Theorem",
    "Proof",
    "Algorithm",
    "Summary",
}


@dataclass
class StructuredBlock:
    text: str
    block_type: str
    page: int
    source_file: str
    chapter: str = ""
    section: str = ""


# Regex patterns for deterministic structure cues
RULES = [
    ("Definition", re.compile(r"^(?:Definition|Def\.?)\s*(?:\d+(?:\.\d+)*)?\s*[:\.-]?", re.IGNORECASE)),
    ("Theorem",    re.compile(r"^(?:Theorem|Lemma|Proposition|Corollary)\s*(?:\d+(?:\.\d+)*)?\s*[:\.-]?", re.IGNORECASE)),
    ("Proof",      re.compile(r"^(?:Proof|Proof\s+of\s+[\w\s]+)\s*[:\.-]?", re.IGNORECASE)),
    ("Algorithm",  re.compile(r"^(?:Algorithm|Procedure|Pseudocode)\s*(?:\d+(?:\.\d+)*)?\s*[:\.-]?", re.IGNORECASE)),
    ("Example",    re.compile(r"^(?:Example|Worked\s+Example)\s*(?:\d+(?:\.\d+)*)?\s*[:\.-]?", re.IGNORECASE)),
    ("Exercise",   re.compile(r"^(?:Exercise|Problem|Question|Practice)\s*(?:\d+(?:\.\d+)*)?\s*[:\.-]?", re.IGNORECASE)),
    ("Summary",    re.compile(r"^(?:Summary|Key\s+Takeaways|Chapter\s+Summary|Review\s+Summary)\s*[:\.-]?", re.IGNORECASE)),
]


def detect_block_type(block: ParsedBlock) -> str:
    """Detects the educational block type using layout and text cues."""
    if block.is_heading:
        if block.chapter and block.text.strip().lower().startswith("chapter"):
            return "Chapter"
        return "Section"

    first_line = block.text.strip().splitlines()[0].strip()

    # Rule-based matching against textbook prefixes
    for block_type, pattern in RULES:
        if pattern.search(first_line):
            return block_type

    # Secondary check within the first 100 characters
    snippet = block.text[:120].strip()
    for block_type, pattern in RULES:
        if pattern.search(snippet):
            return block_type

    # Default educational exposition block
    return "Explanation"


def detect_educational_structures(blocks: List[ParsedBlock]) -> List[StructuredBlock]:
    """Processes a list of ParsedBlocks and tags each with its educational structure type."""
    structured = []
    current_chapter = ""
    current_section = ""

    for b in blocks:
        if b.chapter:
            current_chapter = b.chapter
        if b.section:
            current_section = b.section

        b_type = detect_block_type(b)
        structured.append(
            StructuredBlock(
                text=b.text,
                block_type=b_type,
                page=b.page,
                source_file=b.source_file,
                chapter=current_chapter,
                section=current_section,
            )
        )

    return structured
