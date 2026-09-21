"""
Educational Dataset Construction Pipeline - Main Coordinator
Executes all 10 steps:
  1. Document Parsing
  2. Educational Structure Detection
  3. Structure-Aware Chunking
  4. Concept Extraction
  5. Concept Normalization & Entity Linking
  6. Definition Extraction
  7. Relation Extraction
  8. Relation Classification (5-type controlled ontology)
  9. Educational Weight Assignment
  10. Dataset Construction ({concepts.csv, relations.csv})
  -> Downstream Educational Knowledge Graph (Pyvis)
"""

import re
from pathlib import Path
from typing import Optional, Tuple
import networkx as nx

from .parser import parse_document
from .structure_detector import detect_educational_structures
from .chunker import create_structure_aware_chunks
from .concept_extractor import extract_concepts_for_chunk
from .normalizer import ConceptNormalizer
from .definition_extractor import extract_grounded_definition
from .relation_extractor import RelationManager
from .dataset_builder import build_and_save_dataset
from .graph_stats import compute_graph_statistics
from .graph_builder import build_educational_graph


def run_educational_pipeline(
    data_dir: str = "cureus",
    input_base_dir: str = "./data_input",
    output_base_dir: str = "./data_output",
    output_html: str = "./docs/index.html",
    model: Optional[str] = "zephyr:latest",
    use_llm: bool = True,
    show_edge_labels: bool = False,
    show_edge_tooltips: bool = True,
) -> Tuple[Path, Path, nx.DiGraph]:
    """
    Executes the complete Educational Dataset Construction Pipeline.
    """
    input_path = Path(input_base_dir) / data_dir
    output_path = Path(output_base_dir) / data_dir
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  EDUCATIONAL DATASET CONSTRUCTION PIPELINE")
    print(f"{'='*65}")
    print(f"  Dataset Input  : {input_path.resolve()}")
    print(f"  Dataset Output : {output_path.resolve()}")
    print(f"  LLM Enabled    : {use_llm} (Model: {model})")
    print(f"{'='*65}\n")

    # -------------------------------------------------------------------------
    # Step 1: Document Parsing
    # -------------------------------------------------------------------------
    print("[*] Step 1: Document Parsing...")
    doc_files = []
    if input_path.is_file():
        doc_files = [input_path]
    elif input_path.is_dir():
        doc_files = sorted(list(input_path.glob("*.pdf")) + list(input_path.glob("*.txt")))

    # Also check parent directory if input_path folder is empty
    if not doc_files and Path(input_base_dir).exists():
        doc_files = sorted(list(Path(input_base_dir).glob(f"{data_dir}*.pdf")) + list(Path(input_base_dir).glob(f"{data_dir}*.txt")))

    if not doc_files:
        raise FileNotFoundError(f"No document files found in {input_path} or matching {data_dir} in {input_base_dir}")

    all_parsed_blocks = []
    for f in doc_files:
        print(f"    - Parsing file: {f.name} ...")
        blocks = parse_document(f)
        all_parsed_blocks.extend(blocks)
    print(f"[+] Step 1 Complete: Extracted {len(all_parsed_blocks)} structural blocks.")

    # -------------------------------------------------------------------------
    # Step 2: Educational Structure Detection
    # -------------------------------------------------------------------------
    print("[*] Step 2: Educational Structure Detection...")
    structured_blocks = detect_educational_structures(all_parsed_blocks)
    type_counts = {}
    for sb in structured_blocks:
        type_counts[sb.block_type] = type_counts.get(sb.block_type, 0) + 1
    print(f"[+] Step 2 Complete: Detected structures -> {type_counts}")

    # -------------------------------------------------------------------------
    # Step 3: Structure-Aware Educational Chunking
    # -------------------------------------------------------------------------
    print("[*] Step 3: Structure-Aware Educational Chunking...")
    chunks = create_structure_aware_chunks(structured_blocks)
    print(f"[+] Step 3 Complete: Created {len(chunks)} educational chunks.")

    # -------------------------------------------------------------------------
    # Steps 4, 5, 6: Concept Extraction, Normalization & Definitions (Pass 1)
    # -------------------------------------------------------------------------
    print("[*] Steps 4-6: Extracting and Normalizing Concepts across all chunks...")
    normalizer = ConceptNormalizer()
    relation_manager = RelationManager(normalizer)

    llm_extract_func = None
    if use_llm:
        try:
            from helpers.prompts import educationalPrompt
            llm_extract_func = educationalPrompt
        except ImportError:
            pass

    # Pass 1: Extract and register concepts from all chunks
    llm_results_by_chunk = {}
    for idx, chunk in enumerate(chunks, 1):
        llm_concepts = None
        llm_relations = None

        if use_llm and llm_extract_func:
            try:
                llm_res = llm_extract_func(chunk.text, model=model)
                if isinstance(llm_res, dict):
                    llm_concepts = llm_res.get("concepts", [])
                    llm_relations = llm_res.get("relations", [])
                    llm_results_by_chunk[chunk.chunk_id] = llm_relations
            except Exception:
                pass

        extracted = extract_concepts_for_chunk(chunk, llm_concepts=llm_concepts)

        for c in extracted:
            c_name = c["concept_name"]
            c_def = c.get("definition", "")
            c_ev = c.get("evidence", "")

            if not c_def:
                grounded = extract_grounded_definition(c_name, chunk.text)
                if grounded:
                    c_def, c_ev = grounded

            normalizer.register_concept(
                name=c_name,
                aliases=c.get("aliases", []),
                concept_type=c.get("concept_type", "Component"),
                definition=c_def,
                chapter=chunk.chapter,
                section=chunk.section,
                page=chunk.page,
                chunk_id=chunk.chunk_id,
                evidence=c_ev,
            )

    # -------------------------------------------------------------------------
    # Steps 7, 8, 9: Relation Extraction, Ontology Classification & Weighting (Pass 2)
    # -------------------------------------------------------------------------
    print("[*] Steps 7-9: Extracting and Classifying Relations into Controlled Ontology...")

    # A. Ingest and classify any precomputed relations from existing graph.csv
    precomputed_graph = output_path / "graph.csv"
    if precomputed_graph.exists():
        import pandas as pd
        print(f"[*] Ingesting & classifying relations from {precomputed_graph.name}...")
        df_pre = pd.read_csv(precomputed_graph, sep="|", dtype=str).fillna("")
        src_col = "node_1" if "node_1" in df_pre.columns else "source"
        tgt_col = "node_2" if "node_2" in df_pre.columns else "target"
        rel_col = "edge" if "edge" in df_pre.columns else "relationship"

        for _, row in df_pre.iterrows():
            s_name = row.get(src_col, "").strip()
            t_name = row.get(tgt_col, "").strip()
            raw_rel = row.get(rel_col, "").strip()
            chunk_ref = row.get("chunk_id", "")
            if s_name and t_name:
                normalizer.register_concept(s_name)
                normalizer.register_concept(t_name)
                relation_manager.add_relation(
                    source_name=s_name,
                    target_name=t_name,
                    relation_type=raw_rel or "Application",
                    evidence=raw_rel,
                    chunk_id=chunk_ref,
                )

    # B. Add LLM-extracted relations if any
    for chunk_id, rels in llm_results_by_chunk.items():
        for r in rels:
            relation_manager.add_relation(
                source_name=r.get("source", ""),
                target_name=r.get("target", ""),
                relation_type=r.get("relation_type", "Application"),
                evidence=r.get("evidence", ""),
                chunk_id=chunk_id,
                # LLM rates relations 1-10; normalize onto the same [0, 1]
                # scale as the AHP-derived weight so the two are comparable.
                weight=(int(r["weight"]) - 1) / 9 if r.get("weight") else None,
            )

    # C. Extract sentence-level co-occurrences using the full concept registry
    for chunk in chunks:
        sentences = re.split(r"(?<=[.?!])\s+", chunk.text)
        relation_manager.extract_relations_from_sentences(
            sentences=sentences,
            page=chunk.page,
            chunk_id=chunk.chunk_id,
        )

    # -------------------------------------------------------------------------
    # Step 10: Dataset Construction ({concepts.csv, relations.csv})
    # -------------------------------------------------------------------------
    print("\n[*] Step 10: Dataset Construction...")
    concepts_csv, relations_csv = build_and_save_dataset(
        normalizer=normalizer,
        relation_manager=relation_manager,
        output_dir=output_path,
    )

    # -------------------------------------------------------------------------
    # Compute Graph Statistics (Knowledge Graph Repository cache)
    # -------------------------------------------------------------------------
    print("\n[*] Computing Graph Statistics...")
    concept_stats_csv, graph_summary_json, graph_summary = compute_graph_statistics(
        concepts_csv=concepts_csv,
        relations_csv=relations_csv,
        output_dir=output_path,
    )

    # -------------------------------------------------------------------------
    # Downstream: Educational Knowledge Graph
    # -------------------------------------------------------------------------
    print("\n[*] Building Downstream Educational Knowledge Graph...")
    G = build_educational_graph(
        concepts_csv=concepts_csv,
        relations_csv=relations_csv,
        output_html=output_html,
        show_edge_labels=show_edge_labels,
        show_edge_tooltips=show_edge_tooltips,
    )

    # Summary
    print(f"\n{'='*65}")
    print("  EDUCATIONAL PIPELINE EXECUTION COMPLETE")
    print(f"{'='*65}")
    print(f"  Canonical Concepts : {G.number_of_nodes()}")
    print(f"  Classified Relations: {G.number_of_edges()}")
    print(f"  Graph Density      : {graph_summary.get('density')}")
    print(f"  Communities        : {graph_summary.get('communities')}")
    print(f"  Output Datasets    : {concepts_csv.name}, {relations_csv.name}")
    print(f"  Graph Stats Cache  : {concept_stats_csv.name}, {graph_summary_json.name}")
    print(f"  Interactive Graph  : {Path(output_html).resolve()}")
    print(f"{'='*65}\n")

    return concepts_csv, relations_csv, G
