"""
Step 3: Structure-Aware Educational Chunking
Divides the textbook according to educational boundaries instead of arbitrary
fixed token windows:
  - Definitions and Theorems remain intact wherever possible.
  - Examples and Exercises become separate, clean chunks.
  - Explanations are bundled within section and chapter boundaries.
  - Assigns unique chunk_id, chapter, section context, page, and educational block type.
"""

import uuid
from dataclasses import dataclass
from typing import List
from .structure_detector import StructuredBlock


@dataclass
class EducationalChunk:
    chunk_id: str
    text: str
    block_type: str
    chapter: str
    section: str
    page: int
    source_file: str


def create_structure_aware_chunks(
    blocks: List[StructuredBlock],
    target_size: int = 1500,
    max_size: int = 2200,
) -> List[EducationalChunk]:
    """
    Groups structured blocks into educational chunks adhering to pedagogical boundaries.
    """
    chunks: List[EducationalChunk] = []
    standalone_types = {"Definition", "Theorem", "Proof", "Algorithm", "Example", "Exercise", "Summary"}

    current_buffer: List[str] = []
    current_chars = 0
    current_chapter = ""
    current_section = ""
    current_page = 1
    current_source = ""
    current_block_type = "Explanation"

    def flush_buffer():
        nonlocal current_buffer, current_chars
        if not current_buffer:
            return
        combined_text = "\n\n".join(current_buffer).strip()
        if combined_text:
            chunks.append(
                EducationalChunk(
                    chunk_id=uuid.uuid4().hex,
                    text=combined_text,
                    block_type=current_block_type,
                    chapter=current_chapter,
                    section=current_section,
                    page=current_page,
                    source_file=current_source,
                )
            )
        current_buffer = []
        current_chars = 0

    for b in blocks:
        # If heading only (Chapter / Section without body), update context
        if b.block_type in {"Chapter", "Section"}:
            flush_buffer()
            current_chapter = b.chapter
            current_section = b.section
            current_page = b.page
            current_source = b.source_file
            continue

        # If it's a standalone atomic block (Definition, Theorem, Example, etc.)
        if b.block_type in standalone_types:
            flush_buffer()
            # If the standalone block itself is within acceptable size, make it a single chunk
            if len(b.text) <= max_size:
                chunks.append(
                    EducationalChunk(
                        chunk_id=uuid.uuid4().hex,
                        text=b.text.strip(),
                        block_type=b.block_type,
                        chapter=b.chapter or current_chapter,
                        section=b.section or current_section,
                        page=b.page,
                        source_file=b.source_file,
                    )
                )
            else:
                # If exceptionally long, break along paragraphs
                paras = b.text.split("\n\n")
                sub_buf = []
                sub_len = 0
                for p in paras:
                    if sub_len + len(p) > target_size and sub_buf:
                        chunks.append(
                            EducationalChunk(
                                chunk_id=uuid.uuid4().hex,
                                text="\n\n".join(sub_buf).strip(),
                                block_type=b.block_type,
                                chapter=b.chapter or current_chapter,
                                section=b.section or current_section,
                                page=b.page,
                                source_file=b.source_file,
                            )
                        )
                        sub_buf = [p]
                        sub_len = len(p)
                    else:
                        sub_buf.append(p)
                        sub_len += len(p)
                if sub_buf:
                    chunks.append(
                        EducationalChunk(
                            chunk_id=uuid.uuid4().hex,
                            text="\n\n".join(sub_buf).strip(),
                            block_type=b.block_type,
                            chapter=b.chapter or current_chapter,
                            section=b.section or current_section,
                            page=b.page,
                            source_file=b.source_file,
                        )
                    )
            # Reset current context
            current_chapter = b.chapter or current_chapter
            current_section = b.section or current_section
            current_page = b.page
            current_source = b.source_file
            current_block_type = "Explanation"
            continue

        # For regular Explanations, accumulate up to target_size
        # Flush if section or chapter changes
        if (b.section and b.section != current_section) or (b.chapter and b.chapter != current_chapter):
            flush_buffer()
            current_chapter = b.chapter or current_chapter
            current_section = b.section or current_section

        if current_chars + len(b.text) > target_size and current_buffer:
            flush_buffer()

        current_buffer.append(b.text.strip())
        current_chars += len(b.text)
        current_page = b.page
        current_source = b.source_file
        current_block_type = "Explanation"

    flush_buffer()
    return chunks
