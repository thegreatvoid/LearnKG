# Educational pipeline walkthrough (data lineage with real CSV records)

Dataset: CK-12 Basic Geometry (`data_input/ck12_geometry/ck12_basic_geometry_concepts.txt`). Everything below was verified against the code in `educational_pipeline/` and against the CSVs in `data_output/ck12_geometry_steps/`. Figures and Mermaid source are generated from those CSVs by `docs/make_pipeline_figures.py` (no hand-typed values).

| Figure | File |
|---|---|
| 1 Overview, stages 1-10 with one real record per stage | `educational_pipeline_fig1_overview.png/.svg` |
| 2 Concepts: chunking, candidates, normalisation, definitions, final concepts | `educational_pipeline_fig2_concepts.png/.svg` |
| 3 Relations: candidates, classification/merge, weights, final relations | `educational_pipeline_fig3_relations.png/.svg` |
| 4 Final dataset and graph construction | `educational_pipeline_fig4_graph.png/.svg` |
| Editable source (Mermaid) | `educational_pipeline_flowchart.mmd` |

## 0. What is observed versus what the original pipeline writes (read first)

* The original pipeline (`pipeline.run_educational_pipeline`) holds stages 1-9 **in memory** and writes only `concepts.csv` and `relations.csv` (stage 10) plus the HTML graph. The files `01_...csv` to `09_...csv` exist **only because `educational_pipeline/dump_steps.py` re-runs the same functions and logs each step** (that script was added to the repo as a documentation aid; it does not change pipeline behaviour). `10_dataset_*.csv` are the real `build_and_save_dataset` output renamed.
* The dump follows the **rule-based path**: no LLM, no neural prerequisite extractor, no `graph.csv` ingestion. `pipeline.py` has four relation sources (A precomputed `graph.csv`, B LLM relations, C sentence rules/co-occurrence, D neural cross-encoder); only C is exercised. The committed `data_output/ck12_geometry/relations.csv` (90 rows) also contains the 18 neural edges, so it differs from the dump (72 rows).
* In `pipeline.py` stages 4-6 run **interleaved per chunk** (candidates -> register in normaliser -> definition), and stages 7-9 run **inside one call** (`RelationManager.add_relation` classifies, weights and de-duplicates). The 11 files are therefore logical views, not 11 separate program stages.

## 1. Traced example

Chunk `9106de425a374350b2350d77e9b484fc`, section "1.4 Angle Pairs" (409 chars), and relation **R0004: Angle (C0014) -> Vertical Angles (C0016), Part-of, weight 0.3785**. Concept-merge example: **Equilateral Triangle (C0021)** with alias "Equilateral Triangles".

## 2. Stage by stage

| # | Input | Operation (code) | Output | Transformation |
|---|---|---|---|---|
| 1 | source `.txt` | `parser.parse_text_file`: split on blank lines, detect chapter/section headings, estimate page (~2500 chars) | `01_parsed_blocks.csv` (72 rows: page, chapter, section, is_heading, text) | paragraphs -> blocks carrying chapter/section; a heading line and its paragraph stay in one block ("1.4 Angle Pairs\nComplementary angles ...") |
| 2 | 01 | `structure_detector.detect_educational_structures`: regex cues (Definition/Theorem/Example/...), headings -> Chapter/Section, else Explanation | `02_structured_blocks.csv` (72 rows, +block_type) | adds `block_type`; here only Explanation (60) and Chapter (12); text identical to 01 (verified) |
| 3 | 02 | `chunker.create_structure_aware_chunks`: buffer Explanations to 1500 chars, flush on section/chapter change, atomic types stay whole | `03_chunks.csv` (60 rows, uuid `chunk_id`, n_chars) | blocks -> chunks; `chunk_id` is the key used by every later file |
| 4 | 03 chunk text | `concept_extractor.extract_candidate_concepts_from_text`: capitalised phrases, acronyms, quoted terms, "called X", 110-term geometry list, boilerplate filter | `04_concept_candidates.csv` (331 rows: chunk_id, page, chapter, candidate) | 1 chunk -> many candidates; the same name repeats across chunks; no concept id yet |
| 5 | 04 (+06) | `normalizer.register_concept`: clean name, merge exact / plural / acronym matches, others -> aliases | `05_normalized_concepts.csv` (130 rows, `concept_id` C000n) | many candidates -> one canonical concept; 331 -> 130 |
| 6 | candidate name + its chunk text | `definition_extractor.extract_grounded_definition`: "X is/are/refers to ..." else a 30-250 char sentence containing X | `06_concept_definitions.csv` (331 rows: chunk_id, concept, definition, evidence) | each candidate gets a sentence from its own chunk; no model |
| 7 | chunk sentences + registered concepts | `RelationManager.extract_relations_from_sentences`: 38 geometry regex rules; >=2 concepts in a sentence plus a keyword cue | `07_relation_candidates.csv` (192 rows: source_name, target_name, raw_predicate, evidence, chunk_id) | sentences -> proposals (every `add_relation` call) |
| 8 | 07 | `classify_relation` (exact name, keyword, default **Application**); key (source id, target id, type): first -> new edge, later -> merged | `08_relations_classified.csv` (192 rows = 07 + relation_id, classified_type, status) | 192 proposals -> 72 edges (`new` 72, `duplicate_merged` 120) |
| 9 | each new relation | `ahp_components`: `w = .52*S + .24*C + .09*P + .15*E` | `09_relation_weights.csv` (72 rows) | adds weight and its factors (see section 3) |
| 10 | normaliser registry; `RelationManager.relations` | `dataset_builder.build_and_save_dataset` | `10_dataset_concepts.csv` (130), `10_dataset_relations.csv` (72) | registry/list dumped, newlines removed from text fields |
| 11 | the two stage-10 CSVs | `graph_builder.build_educational_graph` (separate downstream stage) | `networkx.DiGraph` -> pyvis HTML | rows -> nodes/edges, see section 4 |

## 3. Edge weight (verified against `relation_extractor.py`, not inferred from the CSV)

R0004: S=0.0741 (Jaccard of the two concepts' definition words), C=min(1, count/3) with count=2, P=1/(1+chapter distance)=1.0, E=0.6 (same chapter, no same section). `0.52*0.0741 + 0.24*(2/3) + 0.09*1.0 + 0.15*0.6 = 0.3785`, equal to the stored weight. Weights supplied by an LLM or the neural extractor (`weight_source = provided`) would bypass the formula; none occur in this dump. On a duplicate the higher weight is kept. There is no threshold: all 72 edges are kept.

## 4. Final graph (verified by running `build_educational_graph` on the stage-10 files)

* `networkx.DiGraph` (directed). Node key = `concept_id`; attributes label, concept_type, definition, tooltip (aliases, chapter, page), then community `group` (Girvan-Newman) and PageRank `size`.
* Edge `source_id -> target_id` with relation_type, weight, colour, tooltip (evidence). Similarity rows also get the reverse edge (130 nodes, 117 edges = 72 relations + 45 reverse edges). pyvis `from_nx` renames edge `weight` to `value`.
* Not in the graph: `weight_source`, `cooccurrence_count`, S/P/E factors, `chunk_id`. Evidence survives only in the tooltip.
* Export: HTML (`docs/ck12_geometry.html` from `run_geometry_pipeline.py`). `graph_stats.py` is a different consumer of the CSVs. The CSVs are not themselves the graph; the graph exists only after this extra stage.

## 5. Lineage: what links records and what does not (checked programmatically)

| Link | Key | Verified |
|---|---|---|
| 01 -> 02 | row position (text identical) | yes, 72/72 |
| 02 -> 03 | none stored | chunks are rebuilt from blocks; no block id in 03 |
| 03 -> 04, 06, 07, 08 | `chunk_id` | all ids exist in 03 |
| 04 -> 05 | **name only** (04 has no concept_id) | 100% of 04 candidates match a 05 name or alias after the normaliser's cleaning |
| 04 <-> 06 | `(chunk_id, name)`; same row count (331) but **not the same row order** | |
| 05 -> 10 concepts | `concept_id` | identical id lists |
| 07 -> 08 | **row position only** (07 has no id; 08 has the same rows plus ids) | identical source/evidence per row |
| 08 -> 09 -> 10 relations | `relation_id` | same 72 ids; 09 = status `new` rows |
| 10 relations -> 10 concepts | `source_id`/`target_id` | all endpoints exist |
| concept location columns | **not the traced chunk** | see below |

Provenance gap worth knowing: for C0014 (Angle) `10_dataset_concepts.csv` shows section "1.3 Rays and Angles", page 4 and chunk `d70036ee...`, not the traced chunk `9106de42...`. `register_concept` replaces a concept's definition, evidence, chapter, section, page and chunk together whenever a **longer** definition appears; so the stored location is that of the longest definition (here "4.4 Triangle Congruence using ASA, AAS, ..."), which is unrelated to the concept's meaning. 05 omits definitions, so this is only visible in 10.

## 6. Observed behaviour worth flagging (observation, not a fix)

* Definitions are sometimes wrong: "Line" in the traced chunk gets "A linear pair is two adjacent angles that form a straight line." and Angle's final definition comes from a triangle-congruence sentence; "Bisector is y figure ..." in section 1.2.
* R0004's relation direction: the geometry regex rule emits `(Angle, Vertical Angles, Part-of)`, i.e. Angle -> Vertical Angles, while the ontology says Part-of means source is a component of target.
* In this run the classification step changes nothing: all 192 raw predicates in 07 are already one of the five type names (the regex rules and keyword cues emit types directly), so `classified_type` equals `raw_predicate` on 192 of 192 rows. The keyword and default-Application paths of `classify_relation` exist but are not exercised here.

## 7. Regenerate

```
python -m educational_pipeline.dump_steps --data-dir ck12_geometry   # rewrites data_output/ck12_geometry_steps/*.csv
python docs/make_pipeline_figures.py                                   # rewrites docs/educational_pipeline_fig*.png/svg and .mmd
```
The script reads only the CSVs, so after any pipeline change rerun both. Change the traced example via `EX_SECTION`, `EX_REL`, `EX_MERGE` at the top of the script. Render the Mermaid file with any Mermaid renderer (mmdc is not installed here).
