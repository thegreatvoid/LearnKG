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


def parse_text_file(filepath: Path) -> List[ParsedBlock]:
    """Parses a plain text file into structured blocks."""
    blocks = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Split into paragraphs by blank lines
    paragraphs = re.split(r"\n\s*\n", content)
    current_chapter = ""
    current_section = ""
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
            text = re.sub(r"(?:---\s*Page\s*(\d+)\s*---|\[Page\s*(\d+)\])", "", text).strip()
            if not text:
                continue

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            heading_info = _detect_heading(lines[0])
            if heading_info and len(lines) == 1:
                level, title = heading_info
                if level == "chapter":
                    current_chapter = title
                else:
                    current_section = title
                blocks.append(
                    ParsedBlock(
                        text=text,
                        page=estimated_page,
                        source_file=filepath.name,
                        chapter=current_chapter,
                        section=current_section,
                        is_heading=True,
                    )
                )
                continue

        blocks.append(
            ParsedBlock(
                text=text,
                page=estimated_page,
                source_file=filepath.name,
                chapter=current_chapter,
                section=current_section,
                is_heading=False,
            )
        )

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
    current_chapter = ""
    current_section = ""

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        paragraphs = re.split(r"\n\s*\n", page_text)

        for p in paragraphs:
            text = p.strip()
            if not text:
                continue

            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines:
                heading_info = _detect_heading(lines[0])
                if heading_info and len(lines) <= 2:
                    level, title = heading_info
                    if level == "chapter":
                        current_chapter = title
                    else:
                        current_section = title
                    blocks.append(
                        ParsedBlock(
                            text=text,
                            page=page_num,
                            source_file=filepath.name,
                            chapter=current_chapter,
                            section=current_section,
                            is_heading=True,
                        )
                    )
                    continue

            blocks.append(
                ParsedBlock(
                    text=text,
                    page=page_num,
                    source_file=filepath.name,
                    chapter=current_chapter,
                    section=current_section,
                    is_heading=False,
                )
            )

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
