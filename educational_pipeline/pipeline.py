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
from .definition_extractor import extract_grounded_definition, find_definition
from .relation_extractor import RelationManager
from .dataset_builder import build_and_save_dataset
from .graph_builder import build_educational_graph


def run_educational_pipeline(
    data_dir: str = "cureus",
    input_base_dir: str = "./data_input",
    output_base_dir: str = "./data_output",
    output_html: str = "./docs/index.html",
    model: Optional[str] = "zephyr:latest",
    use_llm: bool = True,
    use_neural_model: bool = True,
    neural_threshold: float = -0.5,
    embedding_similarity: bool = False,
    definition_policy: str = "first_definitional",
    weighting_scheme: str = "ahp",
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
    full_text = "\n\n".join(b.text for b in all_parsed_blocks)
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
    normalizer = ConceptNormalizer(definition_policy=definition_policy)
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
            c_kind = "llm" if c_def else ""

            if not c_def:
                if definition_policy == "legacy_longest":
                    grounded = extract_grounded_definition(c_name, chunk.text)
                    if grounded:
                        c_def, c_ev = grounded
                        c_kind = "legacy"
                else:
                    found = find_definition(c_name, chunk.text)
                    if found:
                        c_def, c_ev, c_kind = found

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
                definition_kind=c_kind,
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
                    source="graph_csv",
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
                weight=r.get("weight"),  # LLM integer 1-10, stored raw in extractor_scores["llm"]
                source="llm",
            )

    # C. Extract sentence-level co-occurrences using the full concept registry
    for chunk in chunks:
        sentences = re.split(r"(?<=[.?!])\s+", chunk.text)
        relation_manager.extract_relations_from_sentences(
            sentences=sentences,
            page=chunk.page,
            chunk_id=chunk.chunk_id,
        )

    # D. Generate Candidate Pairs with Provenance (Phase 3)
    print("\n[*] Generating Multi-Channel Candidate Pairs with Provenance...")
    import pandas as pd
    import json
    from .candidate_generator import CandidateGenerator
    cand_gen = CandidateGenerator(normalizer, chunks)
    candidate_pairs = cand_gen.generate_candidates(per_concept_limit=20, max_total_candidates=3000)
    cand_csv = output_path / "candidate_pairs.csv"
    pd.DataFrame([c.to_dict() for c in candidate_pairs]).to_csv(cand_csv, index=False)
    print(f"[+] Candidate pairs generated: {len(candidate_pairs)} -> {cand_csv.name}")

    # E. LLM-Based Multi-Relation Extraction & Automatic Verification (Phases 4 & 5)
    verification_records = []
    if use_llm:
        print("\n[*] Initializing Multi-Relation LLM Extractor & Verifier...")
        from .multi_relation_extractor import MultiRelationExtractor
        from .verifier import EvidenceVerifier
        from kg_extract.backend import OllamaBackend
        backend = None
        try:
            backend = OllamaBackend(model=model or "qwen2.5:3b-instruct")
        except Exception as e:
            print(f"[!] Warning: Ollama backend unavailable ({e}); proceeding without live LLM.")

        if backend is not None:
            extractor = MultiRelationExtractor(backend=backend)
            print(f"[*] Extracting relationships over {min(len(candidate_pairs), 100)} top candidate pairs...")
            proposals = extractor.extract_all(candidate_pairs[:100])
            print(f"[+] LLM extraction complete: {extractor.counters['accepted_candidates']} accepted, {extractor.counters['rejected_candidates']} rejected.")

            verifier = EvidenceVerifier(full_text=full_text, normalizer=normalizer, verifier_backend=backend)
            accepted_recs, rejected_recs = verifier.verify_all(proposals)
            verification_records = [r.to_dict() for r in (accepted_recs + rejected_recs)]

            diag_path = output_path / "verification_diagnostics.json"
            diag_path.write_text(json.dumps([r.to_dict() for r in rejected_recs], indent=2))
            print(f"[+] Automatic Evidence Verification: {len(accepted_recs)} verified supported, {len(rejected_recs)} rejected/uncertain -> {diag_path.name}")

            for rec in accepted_recs:
                p = rec.proposal
                rel = relation_manager.add_relation(
                    source_name=p.source_name,
                    target_name=p.target_name,
                    relation_type=p.relation_type,
                    evidence=p.evidence_quote,
                    source="llm_verified",
                )
                if rel:
                    rel.verification_status = rec.status
                    rel.extraction_confidence = rec.confidence
                    rel.evidence_support = 1.0 if rec.quote_in_text else 0.5

    # F. Extract Neural Prerequisite Relations using Cross-Encoder on GPU/CPU
    if use_neural_model:
        try:
            from .neural_prerequisite_extractor import NeuralPrerequisiteExtractor
            extractor = NeuralPrerequisiteExtractor(threshold=neural_threshold)
            neural_rels = extractor.extract_prerequisites(normalizer=normalizer, chunks=chunks)
            for nr in neural_rels:
                relation_manager.add_relation(
                    source_name=nr["source_name"],
                    target_name=nr["target_name"],
                    relation_type=nr["relation_type"],
                    evidence=nr["evidence"],
                    page=nr.get("page", 1),
                    chunk_id=nr.get("chunk_id", ""),
                    weight=nr.get("weight", None),  # rescaled cross-encoder logit, stored raw
                    source="neural",
                )
        except Exception as e:
            print(f"[-] Neural extraction skipped due to error: {e}")

    # G. Evidence Verification for Rule/Neural Edges
    from .verifier import EvidenceVerifier
    fallback_verifier = EvidenceVerifier(full_text=full_text, normalizer=normalizer)
    for r in relation_manager.relations:
        if r.verification_status == "UNVERIFIED":
            quote_ok = fallback_verifier.check_quote_in_source(r.evidence)
            r.verification_status = "VERIFIED_SUPPORTED" if quote_ok else "INSUFFICIENT_EVIDENCE"
            r.evidence_support = round(min(1.0, (r.cooccurrence_count / 3.0) * 0.5 + (1.0 if quote_ok else 0.0) * 0.5), 4)

    # Step 9: edge weights from the whole text (co-occurrence and sections need every chunk)
    relation_manager.finalize_weights(chunks, compute_embeddings=embedding_similarity, scheme=weighting_scheme)
    print(f"[+] Relation stats: {dict(relation_manager.stats)}")

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
    # Comprehensive Multi-Relation Graph Evaluation (Phase 7)
    # -------------------------------------------------------------------------
    print("\n[*] Running Comprehensive Multi-Relation Graph Evaluation...")
    try:
        from .evaluation import GraphEvaluator
        evaluator = GraphEvaluator(
            concepts_df=pd.read_csv(concepts_csv),
            relations_df=pd.read_csv(relations_csv),
            source_text=full_text,
        )
        eval_report = evaluator.run_full_evaluation(verification_records=verification_records)
        eval_report_path = output_path / "evaluation_report.json"
        eval_report_path.write_text(json.dumps(eval_report, indent=2))
        print(f"[+] Comprehensive evaluation report generated at: {eval_report_path}")
    except Exception as e:
        print(f"[-] Evaluation report generation error: {e}")

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
    print(f"  Output Datasets    : {concepts_csv.name}, {relations_csv.name}")
    print(f"  Interactive Graph  : {Path(output_html).resolve()}")
    print(f"{'='*65}\n")

    return concepts_csv, relations_csv, G
