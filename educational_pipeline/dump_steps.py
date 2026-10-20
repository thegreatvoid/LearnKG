"""Run the educational pipeline step by step and save each step's intermediate output as CSV.

  python -m educational_pipeline.dump_steps --data-dir ck12_geometry --out data_output/ck12_geometry_steps

Files (one per pipeline step; steps 4-6 and 7-9 run interleaved in pipeline.py, so they are captured separately here):
  01_parsed_blocks.csv       parser output
  02_structured_blocks.csv   structure detection (block_type)
  03_chunks.csv              structure-aware chunks
  04_concept_candidates.csv  raw candidates per chunk (before normalisation / definitions)
  05_normalized_concepts.csv after the normaliser merged duplicates and aliases
  06_concept_definitions.csv grounded definition + evidence sentence per concept
  07_relation_candidates.csv every relation proposal, raw predicate, before classification
  08_relations_classified.csv the same proposals after classification into the 5 types (+dedup status)
  09_relation_weights.csv    the four AHP factors and final weight per relation
  10_dataset_{concepts,relations}.csv final dataset (same as dataset_builder output)
LLM and neural steps are off (rule-based path) so the dump is deterministic and needs no model.
"""

import argparse
import re
from pathlib import Path

import pandas as pd

from .chunker import create_structure_aware_chunks
from .concept_extractor import extract_candidate_concepts_from_text, extract_concepts_for_chunk
from .dataset_builder import build_and_save_dataset
from .definition_extractor import find_definition
from .normalizer import ConceptNormalizer
from .parser import parse_document
from .relation_extractor import RelationManager, classify_relation
from .structure_detector import detect_educational_structures


class LoggingRelationManager(RelationManager):
    """Records every add_relation call (step 7), its classified type (step 8) and weight factors (step 9)."""

    def __init__(self, normalizer):
        super().__init__(normalizer)
        self.raw_log = []

    def add_relation(self, source_name, target_name, relation_type, evidence, page=1, chunk_id="", weight=None,
                     source="unspecified"):
        before = len(self.relations)
        rel = super().add_relation(source_name, target_name, relation_type, evidence, page, chunk_id, weight, source)
        self.raw_log.append({
            "source_name": source_name, "target_name": target_name, "raw_predicate": relation_type,
            "classified_type": classify_relation(relation_type), "evidence": evidence, "page": page,
            "chunk_id": chunk_id,
            "source": source,
            "status": "rejected" if rel is None else ("new" if len(self.relations) > before else "duplicate_merged"),
            "relation_id": rel.relation_id if rel else ""})
        return rel


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="ck12_geometry")
    ap.add_argument("--input-base", default="./data_input")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out or f"./data_output/{a.data_dir}_steps")
    out.mkdir(parents=True, exist_ok=True)
    inp = Path(a.input_base) / a.data_dir
    files = [inp] if inp.is_file() else sorted(list(inp.glob("*.pdf")) + list(inp.glob("*.txt")))

    blocks = [b for f in files for b in parse_document(f)]
    pd.DataFrame([{"idx": i, "page": b.page, "chapter": b.chapter, "section": b.section, "is_heading": b.is_heading,
                   "text": b.text} for i, b in enumerate(blocks)]).to_csv(out / "01_parsed_blocks.csv", index=False)

    structured = detect_educational_structures(blocks)
    pd.DataFrame([{"idx": i, "block_type": b.block_type, "page": b.page, "chapter": b.chapter, "section": b.section,
                   "text": b.text} for i, b in enumerate(structured)]).to_csv(out / "02_structured_blocks.csv", index=False)

    chunks = create_structure_aware_chunks(structured)
    pd.DataFrame([{"chunk_id": c.chunk_id, "block_type": c.block_type, "page": c.page, "chapter": c.chapter,
                   "section": c.section, "n_chars": len(c.text), "text": c.text} for c in chunks]
                 ).to_csv(out / "03_chunks.csv", index=False)

    cand_rows, def_rows = [], []
    normalizer = ConceptNormalizer(definition_policy="first_definitional")  # same as pipeline default
    manager = LoggingRelationManager(normalizer)
    for ch in chunks:
        for name in sorted(extract_candidate_concepts_from_text(ch.text)):
            cand_rows.append({"chunk_id": ch.chunk_id, "page": ch.page, "chapter": ch.chapter, "candidate": name})
        for c in extract_concepts_for_chunk(ch):
            d, ev = c.get("definition", ""), c.get("evidence", "")
            kind = "llm" if d else ""
            if not d:
                g = find_definition(c["concept_name"], ch.text)
                if g:
                    d, ev, kind = g
            def_rows.append({"chunk_id": ch.chunk_id, "concept": c["concept_name"], "definition": d, "evidence": ev,
                             "definition_kind": kind})
            normalizer.register_concept(name=c["concept_name"], aliases=c.get("aliases", []),
                                        concept_type=c.get("concept_type", "Component"), definition=d,
                                        chapter=ch.chapter, section=ch.section, page=ch.page, chunk_id=ch.chunk_id,
                                        evidence=ev, definition_kind=kind)
    pd.DataFrame(cand_rows).to_csv(out / "04_concept_candidates.csv", index=False)
    pd.DataFrame([{"concept_id": c.concept_id, "concept_name": c.concept_name, "aliases": ", ".join(sorted(c.aliases)),
                   "concept_type": c.concept_type, "chapter": c.chapter, "page": c.page}
                  for c in normalizer.get_all_concepts()]).to_csv(out / "05_normalized_concepts.csv", index=False)
    pd.DataFrame(def_rows).to_csv(out / "06_concept_definitions.csv", index=False)

    for ch in chunks:
        manager.extract_relations_from_sentences(re.split(r"(?<=[.?!])\s+", ch.text), ch.page, ch.chunk_id)
    manager.finalize_weights(chunks)  # step 9: weights need the whole text
    log = pd.DataFrame(manager.raw_log)
    log[["source_name", "target_name", "raw_predicate", "evidence", "page", "chunk_id"]].to_csv(
        out / "07_relation_candidates.csv", index=False)
    log.to_csv(out / "08_relations_classified.csv", index=False)
    pd.DataFrame([{"relation_id": r.relation_id, "source_id": r.source_id, "target_id": r.target_id,
                   "relation_type": r.relation_type, "weight": r.weight, "weight_source": r.weight_source,
                   "cooccurrence_count": r.cooccurrence_count, "semantic_similarity": round(r.semantic_similarity, 4),
                   "chapter_proximity": round(r.chapter_proximity, 4),
                   "educational_context": round(r.educational_context, 4), "n_proposals": r.n_proposals,
                   "weight_legacy": r.weight_legacy}
                  for r in manager.relations]).to_csv(out / "09_relation_weights.csv", index=False)

    final = out / "_final"
    c_csv, r_csv = build_and_save_dataset(normalizer, manager, final)
    c_csv.replace(out / "10_dataset_concepts.csv"); r_csv.replace(out / "10_dataset_relations.csv"); final.rmdir()

    print(f"{'step':<28}rows")
    for f in sorted(out.glob("*.csv")):
        print(f"{f.name:<34}{len(pd.read_csv(f))}")


if __name__ == "__main__":
    main()
