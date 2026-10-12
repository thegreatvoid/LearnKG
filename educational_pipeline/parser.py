"""
Step 1: Document Parsing
Converts educational textbooks/documents into machine-readable content
while preserving useful structure:
  - Text content
  - Page numbers
  - Chapter and section headings
  - Paragraph boundaries
  - Tables and formulas
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ParsedBlock:
    text: str
    page: int
    source_file: str
    chapter: str = ""
    section: str = ""
    is_heading: bool = False
    metadata: dict = field(default_factory=dict)


def _detect_heading(line: str) -> Optional[tuple[str, str]]:
    """
    Detects if a line is likely a Chapter or Section heading.
    Returns (level, title) or None.
    """
    s = line.strip()
    if not s or len(s) > 120:
        return None

    # Chapter patterns
    chap_match = re.match(r"^(?:Chapter\s+(\d+|[IVXLCDM]+)[\s:.-]*)(.*)$", s, re.IGNORECASE)
    if chap_match:
        chap_num = chap_match.group(1)
        chap_title = chap_match.group(2).strip() or f"Chapter {chap_num}"
        return ("chapter", f"Chapter {chap_num}: {chap_title}" if chap_title != f"Chapter {chap_num}" else s)

    # Numbered section patterns like "1.2 Section Name" or "Section 3: Title"
    sec_match = re.match(r"^(?:Section\s+(\d+(?:\.\d+)*)[\s:.-]*|\b(\d+\.\d+(?:\.\d+)?)\s+)(.*)$", s, re.IGNORECASE)
    if sec_match:
        sec_num = sec_match.group(1) or sec_match.group(2)
        sec_title = sec_match.group(3).strip()
        return ("section", f"{sec_num} {sec_title}".strip())

    # Common educational top-level headers (All caps or Title Case standalone short lines)
    common_headers = {
        "introduction", "background", "overview", "methods", "methodology",
        "results", "discussion", "conclusion", "summary", "review", "abstract",
        "references", "exercises", "problems", "case study"
    }
    if s.lower() in common_headers:
        return ("section", s.title())

    return None


def _split_paragraph(text: str) -> List[tuple[List[tuple[str, str]], str]]:
    """
    Splits a paragraph into (headings, text) segments, one per heading group.
    Headings are often followed directly by their body text with no blank line in
    between (e.g. a "1.1 Points, Lines, and Planes" line, then "A point is ..."),
    so they must be found inside multi-line paragraphs too. The heading lines stay
    in the segment text so concept extraction still sees them; a segment without
    body text is a pure heading. Inside a multi-line paragraph only short lines not
    ending in a period count as headings, so body lines like "2.5 cm is ..." are
    not mistaken for one.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) == 1:
        info = _detect_heading(lines[0])
        return [([info] if info else [], lines[0])]

    groups: List[tuple[List[tuple[str, str]], List[str], List[str]]] = []  # (headings, heading lines, body lines)
    for line in lines:
        info = _detect_heading(line) if len(line) <= 80 and not line.endswith(".") else None
        if info:
            if not groups or groups[-1][2]:
                groups.append(([], [], []))
            groups[-1][0].append(info)
            groups[-1][1].append(line)
        else:
            if not groups:
                groups.append(([], [], []))
            groups[-1][2].append(line)
    return [(infos, "\n".join(head + body)) for infos, head, body in groups]


def _append_segments(
    blocks: List[ParsedBlock],
    text: str,
    page: int,
    source_file: str,
    state: dict,
) -> None:
    """Appends the blocks of one paragraph, updating state["chapter"/"section"] at headings."""
    for infos, seg in _split_paragraph(text):
        for level, title in infos:
            if level == "chapter":
                state["chapter"] = title
                state["section"] = ""  # sections of the previous chapter do not carry over
            else:
                state["section"] = title
        is_heading = bool(infos) and len(seg.splitlines()) == len(infos)
        blocks.append(
            ParsedBlock(
                text=seg,
                page=page,
                source_file=source_file,
                chapter=state["chapter"],
                section=state["section"],
                is_heading=is_heading,
            )
        )


def parse_text_file(filepath: Path) -> List[ParsedBlock]:
    """Parses a plain text file into structured blocks."""
    blocks = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Split into paragraphs by blank lines
    paragraphs = re.split(r"\n\s*\n", content)
    state = {"chapter": "", "section": ""}
    estimated_page = 1
    char_count = 0

    for p in paragraphs:
        text = p.strip()
        if not text:
            continue

        # Page estimate: ~2500 chars per standard textbook page if no explicit page breaks
        char_count += len(text)
        estimated_page = max(1, (char_count // 2500) + 1)

        # Check explicit page marker like "--- Page 3 ---" or "[Page 3]"
        page_match = re.search(r"(?:---\s*Page\s*(\d+)\s*---|\[Page\s*(\d+)\])", text, re.IGNORECASE)
        if page_match:
            estimated_page = int(page_match.group(1) or page_match.group(2))

        _append_segments(blocks, text, estimated_page, filepath.name, state)

    return blocks


def parse_pdf_file(filepath: Path) -> List[ParsedBlock]:
    """Parses a PDF file using pypdf, extracting page-level and paragraph blocks."""
    blocks = []
    try:
        from pypdf import PdfReader
    except ImportError:
        # Fallback to text extraction if pypdf is missing
        return parse_text_file(filepath)

    reader = PdfReader(str(filepath))
    state = {"chapter": "", "section": ""}

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        paragraphs = re.split(r"\n\s*\n", page_text)

        for p in paragraphs:
            text = p.strip()
            if not text:
                continue

            _append_segments(blocks, text, page_num, filepath.name, state)

    return blocks


def parse_document(filepath: Path | str) -> List[ParsedBlock]:
    """Dispatches document parsing based on file extension."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Document file not found: {path}")

    ext = path.suffix.lower()
    if ext == ".pdf":
        return parse_pdf_file(path)
    else:
        return parse_text_file(path)
