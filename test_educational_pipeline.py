"""
Verification script for Educational Dataset Construction Pipeline.
Executes the pipeline on sample data (cureus), validates CSV schemas,
checks ontology constraints, and generates the knowledge graph.
"""

import sys
from pathlib import Path
import pandas as pd

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from educational_pipeline import (
    run_educational_pipeline,
    CONCEPTS_COLUMNS,
    RELATIONS_COLUMNS,
    VALID_ONTOLOGY_TYPES,
)


def run_verification():
    print("[*] Running Educational Dataset Construction Pipeline Verification...")
    concepts_csv, relations_csv, G = run_educational_pipeline(
        data_dir="cureus",
        use_llm=False,  # deterministic mode for instant, offline verification
        output_html="./docs/index.html",
        show_edge_labels=False,
        show_edge_tooltips=True,
    )

    print("\n" + "=" * 60)
    print("  VALIDATION CHECKS")
    print("=" * 60)

    # 1. File existence
    assert concepts_csv.exists(), f"Missing {concepts_csv}"
    assert relations_csv.exists(), f"Missing {relations_csv}"
    print(f"  [PASS] concepts.csv and relations.csv created.")

    # 2. Schema check for concepts.csv
    df_c = pd.read_csv(concepts_csv)
    assert list(df_c.columns) == CONCEPTS_COLUMNS, (
        f"concepts.csv columns mismatch!\nExpected: {CONCEPTS_COLUMNS}\nGot: {list(df_c.columns)}"
    )
    assert len(df_c) > 0, "concepts.csv has 0 rows!"
    print(f"  [PASS] concepts.csv schema matches exact specification ({len(df_c)} concepts).")

    # 3. Schema check for relations.csv
    df_r = pd.read_csv(relations_csv)
    assert list(df_r.columns) == RELATIONS_COLUMNS, (
        f"relations.csv columns mismatch!\nExpected: {RELATIONS_COLUMNS}\nGot: {list(df_r.columns)}"
    )
    assert len(df_r) > 0, "relations.csv has 0 rows!"
    print(f"  [PASS] relations.csv schema matches exact specification ({len(df_r)} relations).")

    # 4. Ontology constraint check
    invalid_rel_types = set(df_r["relation_type"].unique()) - VALID_ONTOLOGY_TYPES
    assert not invalid_rel_types, f"Invalid relation_types found: {invalid_rel_types}"
    print(f"  [PASS] All relation_types strictly adhere to 5-type ontology: {VALID_ONTOLOGY_TYPES}")
    print(f"         Distribution: {df_r['relation_type'].value_counts().to_dict()}")

    # 5. Referential integrity
    concept_ids = set(df_c["concept_id"].unique())
    source_ids = set(df_r["source_id"].unique())
    target_ids = set(df_r["target_id"].unique())
    assert source_ids.issubset(concept_ids), f"Dangling source_ids: {source_ids - concept_ids}"
    assert target_ids.issubset(concept_ids), f"Dangling target_ids: {target_ids - concept_ids}"
    print(f"  [PASS] Referential integrity satisfied (all source_id and target_id exist in concepts.csv).")

    # 6. Weight bounds (AHP-derived relevance score, normalized to [0, 1])
    assert (df_r["weight"] >= 0).all() and (df_r["weight"] <= 1).all(), "Weights outside [0, 1] range!"
    print(f"  [PASS] Relation weights valid (min={df_r['weight'].min():.2f}, max={df_r['weight'].max():.2f}).")

    # 7. HTML Visualization Output
    html_path = Path("./docs/index.html")
    assert html_path.exists() and html_path.stat().st_size > 1000, "Visualization HTML not created or empty!"
    print(f"  [PASS] docs/index.html successfully generated ({html_path.stat().st_size:,} bytes).")

    # 8. Graph Statistics Repository
    stats_csv = concepts_csv.parent / "concept_stats.csv"
    summary_json = concepts_csv.parent / "graph_summary.json"
    assert stats_csv.exists(), f"Missing {stats_csv}"
    assert summary_json.exists(), f"Missing {summary_json}"
    df_stats = pd.read_csv(stats_csv)
    assert len(df_stats) == len(df_c), "concept_stats.csv row count doesn't match concepts.csv!"
    for col in ["pagerank", "degree_centrality", "betweenness_centrality", "clustering_coefficient", "community"]:
        assert col in df_stats.columns, f"concept_stats.csv missing column: {col}"
    print(f"  [PASS] Graph statistics computed for all {len(df_stats)} concepts ({stats_csv.name}, {summary_json.name}).")

    print("=" * 60)
    print("  ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_verification()
