"""
Step 10: Dataset Construction
Compiles and writes the final structured educational dataset into two CSV files:
  1. concepts.csv
     Columns: [concept_id, concept_name, aliases, concept_type, definition, chapter, section, page, chunk_id, evidence]
  2. relations.csv
     Columns: [relation_id, source_id, target_id, relation_type, weight, page, chunk_id, evidence,
                weight_source, cooccurrence_count, semantic_similarity, chapter_proximity, educational_context,
                n_proposals, sources, extractor_scores, s_jaccard_raw, s_embedding, definitions_valid,
                chapter_missing, educational_context_legacy, weight_legacy, evidence_all]
     Factor definitions: relation_extractor.RelationManager.finalize_weights and docs/ahp_weights.md.
"""

from pathlib import Path
from typing import Tuple
import pandas as pd
from .normalizer import ConceptNormalizer
from .relation_extractor import RelationManager


CONCEPTS_COLUMNS = [
    "concept_id",
    "concept_name",
    "aliases",
    "concept_type",
    "definition",
    "chapter",
    "section",
    "page",
    "chunk_id",
    "evidence",
    "definition_kind",
]

RELATIONS_COLUMNS = [
    "relation_id",
    "source_id",
    "target_id",
    "relation_type",
    "weight",
    "page",
    "chunk_id",
    "evidence",
    "weight_source",
    "cooccurrence_count",
    "semantic_similarity",
    "chapter_proximity",
    "educational_context",
    "n_proposals",
    "sources",
    "extractor_scores",
    "s_jaccard_raw",
    "s_embedding",
    "definitions_valid",
    "chapter_missing",
    "educational_context_legacy",
    "weight_legacy",
    "weight_scheme",
    "weight_ahp",
    "weight_cooc_only",
    "weight_cooc_struct_a0.8",
    "extraction_confidence",
    "evidence_support",
    "relation_weight",
    "verification_status",
    "evidence_all",
]


def build_and_save_dataset(
    normalizer: ConceptNormalizer,
    relation_manager: RelationManager,
    output_dir: Path | str,
) -> Tuple[Path, Path]:
    """
    Constructs and persists concepts.csv and relations.csv to the specified directory.
    Returns (concepts_csv_path, relations_csv_path).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    concepts_file = out_path / "concepts.csv"
    relations_file = out_path / "relations.csv"

    # Build concepts DataFrame
    concept_rows = []
    for c in normalizer.get_all_concepts():
        aliases_str = ", ".join(sorted(c.aliases)) if c.aliases else ""
        concept_rows.append({
            "concept_id": c.concept_id,
            "concept_name": c.concept_name,
            "aliases": aliases_str,
            "concept_type": c.concept_type,
            "definition": c.definition.replace("\n", " ").strip(),
            "chapter": c.chapter,
            "section": c.section,
            "page": c.page,
            "chunk_id": c.chunk_id,
            "evidence": c.evidence.replace("\n", " ").strip(),
            "definition_kind": c.definition_kind,
        })

    df_concepts = pd.DataFrame(concept_rows, columns=CONCEPTS_COLUMNS)
    df_concepts.to_csv(concepts_file, index=False, encoding="utf-8")

    # Build relations DataFrame
    relation_rows = []
    for r in relation_manager.relations:
        relation_rows.append({
            "relation_id": r.relation_id,
            "source_id": r.source_id,
            "target_id": r.target_id,
            "relation_type": r.relation_type,
            "weight": r.weight,
            "page": r.page,
            "chunk_id": r.chunk_id,
            "evidence": r.evidence.replace("\n", " ").strip(),
            "weight_source": r.weight_source,
            "cooccurrence_count": r.cooccurrence_count,
            "semantic_similarity": round(r.semantic_similarity, 4),
            "chapter_proximity": round(r.chapter_proximity, 4),
            "educational_context": round(r.educational_context, 4),
            "n_proposals": r.n_proposals,
            "sources": ";".join(sorted(r.sources)),
            "extractor_scores": ";".join(f"{k}:{v:g}" for k, v in sorted(r.extractor_scores.items())),
            "s_jaccard_raw": r.s_jaccard_raw,
            "s_embedding": r.s_embedding,
            "definitions_valid": r.definitions_valid,
            "chapter_missing": r.chapter_missing,
            "educational_context_legacy": r.educational_context_legacy,
            "weight_legacy": r.weight_legacy,
            "weight_scheme": r.weight_scheme,
            "weight_ahp": r.scheme_weights.get("ahp"),
            "weight_cooc_only": r.scheme_weights.get("cooc_only"),
            "weight_cooc_struct_a0.8": r.scheme_weights.get("cooc_struct_a0.8"),
            "extraction_confidence": getattr(r, "extraction_confidence", 1.0),
            "evidence_support": getattr(r, "evidence_support", 0.0),
            "relation_weight": getattr(r, "relation_weight", r.weight),
            "verification_status": getattr(r, "verification_status", "UNVERIFIED"),
            "evidence_all": " || ".join(e.replace("\n", " ").strip() for e in r.evidence_all),
        })

    df_relations = pd.DataFrame(relation_rows, columns=RELATIONS_COLUMNS)
    df_relations.to_csv(relations_file, index=False, encoding="utf-8")

    print(f"[+] Successfully constructed educational dataset:")
    print(f"    - Concepts  ({len(df_concepts)} rows) : {concepts_file}")
    print(f"    - Relations ({len(df_relations)} rows) : {relations_file}")

    return concepts_file, relations_file
