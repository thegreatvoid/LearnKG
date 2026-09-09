"""
Step 10: Dataset Construction
Compiles and writes the final structured educational dataset into two CSV files:
  1. concepts.csv
     Columns: [concept_id, concept_name, aliases, concept_type, definition, chapter, section, page, chunk_id, evidence]
  2. relations.csv
     Columns: [relation_id, source_id, target_id, relation_type, weight, page, chunk_id, evidence]
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
        })

    df_relations = pd.DataFrame(relation_rows, columns=RELATIONS_COLUMNS)
    df_relations.to_csv(relations_file, index=False, encoding="utf-8")

    print(f"[+] Successfully constructed educational dataset:")
    print(f"    - Concepts  ({len(df_concepts)} rows) : {concepts_file}")
    print(f"    - Relations ({len(df_relations)} rows) : {relations_file}")

    return concepts_file, relations_file
