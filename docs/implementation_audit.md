# Multi-Relation Educational Knowledge Graph: Implementation Audit

**Date:** 2026-10-21  
**Target Domain:** Educational Knowledge Graph Construction (CK-12 Basic Geometry / General Textbooks)  
**Evaluator:** Antigravity System Audit  

---

## 1. Executive Summary

This audit inspects the complete multi-relation educational knowledge graph construction and evaluation pipeline across the `educational_pipeline`, `kg_extract`, and `kg_eval` packages.

The primary objective is to evaluate and improve the pipeline to reliably extract five educational relation types:
1. **Prerequisite** (directed: foundational dependency)
2. **Similarity** (symmetric: conceptual or functional equivalence/analogy)
3. **Part-of** (directed: component-to-whole meronymy)
4. **Application** (directed: concept-to-use/domain)
5. **Extension** (directed: base concept to generalization/enrichment)

### Key Findings
- **Prerequisite evaluation** has a rigorous external ground truth benchmark (**AL-CPL** Geometry, 1,681 pairs, 524 positives). Baseline extraction achieves **Precision = 0.700**, **Recall = 0.024**, **F1 = 0.047** on matched pairs with strict direction; textbook order baseline achieves **Recall = 0.959**, **Precision = 0.559**.
- **The other four relations** (Similarity, Part-of, Application, Extension) have **no human-annotated ground-truth dataset**. Previous outputs relied either on keyword regexes or uncalibrated prompt scores. No ground-truth precision/recall can be claimed for them without fabrication; instead, reference-free quality indicators must be tracked.
- **Taxonomic vs. Meronymic Confusion:** Verified bugs in `educational_pipeline/relation_extractor.py` and `kg_extract/score.py` define "Part-of" to include `"is a type of"` and `"special case of"`, confounding hyponymy with meronymy.
- **Textbook Order Leakage in Prerequisite Rules:** When a keyword fires for Prerequisite in `relation_extractor.py`, direction is resolved by textbook page order `(c1.page <= c2.page)` rather than syntactic/semantic position relative to the cue word.
- **Factor Weighting:** The Analytic Hierarchy Process (AHP) formulation ($CR = 0.022$) combines $S$ (definition lexical overlap), $C$ (sentence co-occurrence), $P$ (chapter proximity), and $E$ (section Jaccard). Query-ranking evaluation reveals that $C$ alone achieves $NDCG@10 = 0.716$ vs AHP $0.708$, while $S$ and $P$ alone perform near random ranking.

---

## 2. Pipeline Architecture & Subsystem Mapping

The pipeline consists of nine core operations distributed across specific modules:

| Subsystem | Exact Files & Functions | Role & Current Implementation |
|---|---|---|
| **1. Textbook Ingestion & Preprocessing** | `educational_pipeline/parser.py`<br>• `parse_document`<br>• `_parse_txt`<br>• `_parse_pdf`<br>• `clean_text` | Parses raw documents (.txt, .pdf) into structured text blocks (`ParsedBlock`) preserving line and chapter/section markers. |
| **2. Educational Structure Detection** | `educational_pipeline/structure_detector.py`<br>• `detect_educational_structures`<br>`educational_pipeline/chunker.py`<br>• `create_structure_aware_chunks` | Detects pedagogical block types (Explanation, Chapter, Section, Definition, Theorem). Creates `EducationalChunk` items preserving section and chapter context. |
| **3. Concept Extraction & Normalization** | `educational_pipeline/concept_extractor.py`<br>• `extract_concepts_for_chunk`<br>`educational_pipeline/normalizer.py`<br>• `ConceptNormalizer`<br>• `clean_name`<br>• `find_match`<br>`educational_pipeline/definition_extractor.py`<br>• `find_definition`<br>• `extract_grounded_definition` | Extracts candidate noun phrases, cleans surface forms, normalizes aliases, maps to canonical IDs, and extracts first definitional sentences verbatim. |
| **4. Candidate-Pair Generation** | `educational_pipeline/neural_prerequisite_extractor.py`<br>• `extract_prerequisites` (lines 81-105)<br>`kg_extract/pairs.py`<br>• `generate_candidates`<br>• `embedding_neighbors` | `neural_prerequisite_extractor` generates an exhaustive Cartesian product of all concept pairs where $page_A \le page_B$ ($O(V^2)$, 9,372 pairs in CK-12). `kg_extract/pairs.py` uses heuristic candidate generation (sentence co-occurrence, chunk co-occurrence, definition mentions, embedding neighbors, hubs). |
| **5. Rule-Based Relation Extraction** | `educational_pipeline/relation_extractor.py`<br>• `extract_relations_from_sentences`<br>• `pedagogical_rules`<br>• `ONTOLOGY_PATTERNS`<br>• `KEYWORD_RES`<br>• `REVERSED_KEYWORDS` | Pattern matching with regexes. Employs curated pedagogical rules and connective keyword triggers. Handles passive/reversed keyword flipping for Part-of/Application/Extension. |
| **6. LLM-Based Relation Extraction** | `helpers/prompts.py`<br>• `educationalPrompt`<br>• `graphPrompt`<br>`kg_extract/score.py`<br>• `score_pairs`<br>• `pair_prompt`<br>`kg_extract/backend.py`<br>• `OllamaBackend.chat_json` | Calls Ollama models (`qwen2.5:3b-instruct`, `zephyr:latest`). In `educationalPrompt`, extracts open-ended JSON without validation. In `kg_extract/score.py`, scores pairs with swap-sampling. |
| **7. Hybrid Graph Construction** | `educational_pipeline/pipeline.py`<br>• `run_educational_pipeline`<br>`kg_extract/hybrid.py`<br>• `build_hybrid_graph`<br>`kg_extract/consistency.py`<br>• `make_consistent` | Merges relations from precomputed CSVs, rule patterns, neural cross-encoder, and LLM votes. Enforces DAG acyclicity on Prerequisite edges and filters cycles. |
| **8. Edge Deduplication & Direction Handling** | `educational_pipeline/relation_extractor.py`<br>• `RelationManager.add_relation`<br>• `_by_key`<br>• `_proposals` | Deduplicates directed triplets `(source_id, target_id, relation_type)`. Accumulates multiple proposal sources and distinct evidence sentences into `evidence_all`. |
| **9. Edge-Weight Calculation** | `educational_pipeline/relation_extractor.py`<br>• `pair_factors`<br>• `finalize_weights`<br>• `combine`<br>• `AHP_FACTOR_WEIGHTS`<br>• `WEIGHTING_SCHEMES` | Computes factors $S, C, P, E$ globally across all chunks. Combines factors using AHP coefficients (`ahp`), $C$-only (`cooc_only`), or cross-validated coefficients (`cooc_struct_a0.8`). |
| **10. Graph Export & Evaluation** | `educational_pipeline/dataset_builder.py`<br>• `build_and_save_dataset`<br>`educational_pipeline/graph_builder.py`<br>• `build_educational_graph`<br>`kg_eval/prereq_gold.py`<br>`kg_eval/weight_ranking.py`<br>`kg_eval/bigs.py` | Exports `concepts.csv` and `relations.csv`. Generates Pyvis interactive HTML. Evaluates prerequisite accuracy vs AL-CPL and computes NDCG@k query rankings. |

---

## 3. Audit of Edge Weighting and AHP Consistency

### 3.1 Mathematical Formulation
The baseline edge weight formula is:
$$\text{Weight} = 0.52 \cdot S + 0.24 \cdot C + 0.09 \cdot P + 0.15 \cdot E$$

Where:
- **$S$ (Semantic Similarity):** Jaccard word overlap of validated definitions:
  $$\text{valid}(c) \iff \text{subject of defining clause } [A/An/The]\ X\ \text{is/are/has/etc.}$$
  If a definition is invalid or ungrounded, it falls back to the concept name. Range $[0, 1]$.
- **$C$ (Co-occurrence):**
  $$C = \min\left(1.0, \frac{n_{\text{sentences}}}{3}\right)$$
  Counted at the sentence level across the entire document corpus. Undirected.
- **$P$ (Chapter Proximity):**
  $$P = \frac{1}{1 + |k_{\text{src}} - k_{\text{tgt}}|}$$
  Where $k$ is the integer chapter index. If either chapter is missing, defaults to neutral $0.5$.
- **$E$ (Educational Context):**
  $$E = \text{Jaccard}(\text{sections}(\text{src}), \text{sections}(\text{tgt}))$$
  Section co-mention overlap across parsed textbook sections.

### 3.2 AHP Consistency Analysis
From `docs/ahp_weights.md`, the Saaty comparison matrix is:

$$A = \begin{pmatrix} 1 & 3 & 5 & 3 \\ 1/3 & 1 & 3 & 2 \\ 1/5 & 1/3 & 1 & 1/2 \\ 1/3 & 1/2 & 2 & 1 \end{pmatrix}$$

- **Principal Eigenvalue ($\lambda_{\max}$):** $\approx 4.06$
- **Consistency Index ($CI$):** $(4.06 - 4) / 3 = 0.020$
- **Random Index ($RI$, $n=4$):** $0.90$
- **Consistency Ratio ($CR$):** $0.020 / 0.90 = 0.022 < 0.10$

**Audit Finding:** The comparison matrix is mathematically consistent ($CR = 0.022 \ll 0.10$). However, consistency only proves the internal coherence of subjective judgments; it does not guarantee empirical predictive power.

### 3.3 Empirical Ranking Behavior vs. AL-CPL Ground Truth
Running `kg_eval.weight_ranking` on the 892 matched AL-CPL candidate pairs reveals:

| Scheme / Factor | Formula | NDCG@5 (95% CI) | NDCG@10 (95% CI) | vs AHP ($\Delta$ @10) |
|---|---|---|---|---|
| **Random baseline** | Uniform tie-break | 0.483 [0.421, 0.543] | 0.577 [0.515, 0.635] | -0.131 |
| **AHP Baseline** | $0.52 S + 0.24 C + 0.09 P + 0.15 E$ | 0.620 [0.551, 0.693] | 0.708 [0.656, 0.766] | Baseline |
| **Co-occurrence Only ($C$)** | $1.0 C$ | 0.661 [0.598, 0.723] | 0.716 [0.664, 0.770] | +0.007 ($p=0.678$) |
| **CV-Optimized ($0.8 C + 0.2 E$)** | $0.8 C + 0.2 E$ | 0.665 [0.602, 0.728] | 0.731 [0.679, 0.783] | +0.022 ($p=0.231$) |
| **Semantic Similarity ($S$) Only** | $1.0 S$ | 0.471 [0.395, 0.547] | 0.589 [0.525, 0.652] | -0.119 ($p < 0.001$) |
| **Chapter Proximity ($P$) Only** | $1.0 P$ | 0.489 [0.414, 0.559] | 0.605 [0.536, 0.668] | -0.103 ($p < 0.001$) |
| **Educational Context ($E$) Only** | $1.0 E$ | 0.598 [0.533, 0.665] | 0.684 [0.632, 0.736] | -0.024 |
| **Book Order Gate $\times C$** | Order $\times C$ | 0.822 [0.779, 0.865] | 0.859 [0.825, 0.892] | +0.151 ($p < 0.0001$) |
| **Book Order Gap alone** | Chapter/page gap | 0.868 [0.814, 0.918] | 0.891 [0.848, 0.932] | +0.183 ($p < 0.0001$) |

**Observations:**
1. $S$ (definition lexical overlap) and $P$ (chapter proximity) individually perform no better than random ranking ($NDCG@10 \approx 0.589$ and $0.605$ vs random $0.577$).
2. $C$ (sentence co-occurrence) carries almost all predictive signal for ranking prerequisites ($NDCG@10 = 0.716$), outperforming the 4-factor AHP formula ($0.708$).
3. Book order introduces an overwhelming signal ($NDCG@10 = 0.891$), which must be treated carefully to avoid circular evaluation when comparing pedagogical dependencies.

---

## 4. Verified Bugs and Deficiencies

### Bug 1: Type-of (Hyponymy) Conflated with Part-of (Meronymy)
- **Location:** `educational_pipeline/relation_extractor.py` lines 50, and `kg_extract/score.py` line 23.
- **Code:**
  ```python
  # educational_pipeline/relation_extractor.py: line 50
  "Part-of": [
      ...
      "is a type of", "is a kind of",
  ]
  # kg_extract/score.py: line 23
  "- Part-of: the source is a component or special case of the target (e.g. a radius is part of a circle)."
  ```
- **Observed Effect:** Categorizes "Acute Triangle is a type of Triangle" as `Part-of`. In educational ontology, an acute triangle is not a physical component/meronym of a triangle; it is a hyponym (sub-concept).
- **Reproduction:** When scanning sentences like *"An acute triangle is a kind of triangle with angles less than 90 degrees"*, the system outputs an edge `Acute Triangle -> Triangle (Part-of)`.

### Bug 2: Prerequisite Direction Leakage from Textbook Page Order
- **Location:** `educational_pipeline/relation_extractor.py` lines 576–578.
- **Code:**
  ```python
  if ont == "Prerequisite":
      # No direction in the sentence: earlier-introduced concept -> later one (unchanged rule)
      src_c, tgt_c = (c1, c2) if (c1.page, c1.concept_id) <= (c2.page, c2.concept_id) else (c2, c1)
  ```
- **Observed Effect:** When a Prerequisite keyword is detected in a sentence (e.g. "requires", "depends on"), the system completely ignores whether concept 1 or concept 2 preceded the keyword. Instead, it blindly assigns direction based on which concept appears earlier in the book (`c1.page <= c2.page`).
- **Reproduction:** For a sentence like *"Advanced proofs require line segments"*, where *Advanced Proofs* appears on page 10 and *Line Segments* on page 2, this rule generates `Line Segments -> Advanced Proofs (Prerequisite)` based purely on page order, failing on sentences like *"A requires B"* if $B$ was introduced on a later page.

### Bug 3: Inverted Direction in Hardcoded Pedagogical Rules
- **Location:** `educational_pipeline/relation_extractor.py` lines 497–500.
- **Code:**
  ```python
  (re.compile(r"supplementary angles", re.I), "Angle", "Supplementary", "Part-of"),
  (re.compile(r"complementary angles", re.I), "Angle", "Complementary", "Part-of"),
  (re.compile(r"vertical angles", re.I), "Angle", "Vertical Angles", "Part-of"),
  (re.compile(r"linear pair", re.I), "Angle", "Linear Pair", "Part-of"),
  ```
- **Observed Effect:** The ontology defines `Part-of` as $A \to B$ ($A$ is a component of $B$). Under this rule, `Angle` is the source and `Supplementary` is the target, asserting that *"Angle is a part of Supplementary"*. Furthermore, Supplementary and Complementary are properties or types of angle relationships, not physical wholes.

### Bug 4: Exhaustive $O(V^2)$ Cartesian Product in Neural Candidate Generation
- **Location:** `educational_pipeline/neural_prerequisite_extractor.py` lines 81–105.
- **Code:** Evaluates every concept against every other concept where $page_A \le page_B$.
- **Observed Effect:** For 130 concepts, scores 9,372 pairs using a cross-encoder on CPU, leading to slow runs and high false-positive risk.

### Bug 5: Unvalidated LLM Extraction and Lack of Verification Pipeline
- **Location:** `helpers/prompts.py` (`educationalPrompt`) and `kg_extract/score.py`.
- **Deficiency:**
  - `educationalPrompt` outputs unvalidated free-form JSON with no field check, no quote verification against source text, and no direction verification.
  - LLM self-reported weights (1–10) are hardcoded in prompt instructions (`Prerequisite: 8-10, Part-of: 7-8, Application: 6-7, Extension: 5-6, Similarity: 4-5`), conflating relation type with edge weight.
  - No automated evidence verifier checks whether the quoted sentence exists in the source text or actually supports the relation.

### Bug 6: Bidirectional Credit in Legacy Evaluation Script
- **Location:** `evaluate_prerequisite_extraction.py` line 347.
- **Deficiency:**
  ```python
  extracted_pred = directed_pred or reversed_pred
  ```
  Grants credit to reversed prerequisite edges, reporting misleadingly high recall and F1. (Correctly addressed in `kg_eval/prereq_gold.py`, which enforces strict directionality).

---

## 5. Baseline Metrics on CK-12 Geometry

Executing the baseline pipeline on CK-12 Basic Geometry (`data_input/ck12_geometry/ck12_basic_geometry_concepts.txt`):

### 5.1 Graph Composition
- **Canonical Concepts:** 130 nodes
- **Total Relations Extracted:** 84 unique directed edges (without LLM) / 125 edges in graph view
- **Ontology Distribution:**
  - `Similarity`: 46 edges (54.8%)
  - `Prerequisite`: 27 edges (32.1%)
  - `Part-of`: 7 edges (8.3%)
  - `Application`: 2 edges (2.4%)
  - `Extension`: 2 edges (2.4%)

### 5.2 Prerequisite Benchmark Metrics (vs AL-CPL Ground Truth)
Evaluated with strict directionality via `kg_eval/prereq_gold.py`:

| Evaluated Subset | Pairs ($n$) | Positives | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|
| **All Gold Pairs** | 1,681 | 524 | 0.700 | 0.013 | 0.026 | 0.505 | 0.319 |
| **Matched & Located Pairs** | 1,017 | 291 | **0.700** | **0.024** | **0.047** | **0.510** | **0.300** |
| **Book Order Baseline** | 1,017 | 291 | 0.559 | 0.959 | 0.706 | 0.860 | 0.631 |
| **Co-occurrence Baseline** | 1,017 | 291 | 0.369 | 0.347 | 0.358 | 0.557 | 0.324 |
| **Cooc $\times$ Order Baseline** | 1,017 | 291 | 0.725 | 0.326 | 0.450 | 0.639 | 0.446 |

### 5.3 Reference-Free Baseline Diagnostics for the Other 4 Relations
- Currently, Similarity, Part-of, Application, and Extension have **no verified grounding checks** in the pipeline.
- Quoted evidence strings are unverified verbatim substrings.
- Rejection/insufficient evidence tracking is absent.

---

## 6. Proposed Architecture & Remediation Plan

To address the audited issues, the following improvements are planned:

1. **Formal Relation Schema (`config/relation_schema.yaml`):**
   - Precise definitions, directionality, positive/negative examples, and structural constraints for all 5 relations.
   - Strict rule: reject `is-a` / `type-of` from `Part-of`.
2. **Provenance-Preserving Candidate Generation:**
   - Multi-channel candidate generation: embedding similarity, definitional mentions, co-occurrence, and chapter structure.
   - Bounded candidate pool ($K$ per concept) avoiding $O(V^2)$ evaluation.
   - Retain candidate provenance (method, chunk location, definitions).
3. **Structured LLM Extraction for 4 Relations:**
   - Pydantic schema enforcing structured fields: `source_concept_id`, `target_concept_id`, `relation_type`, `decision`, `evidence_quote`, `evidence_location`, `direction_explanation`, `confidence`, `reasoning_summary`.
   - Programmatic validation of all fields.
4. **Automated Evidence Verification Stage:**
   - Separate verification step checking:
     1. Exact quote existence in source text.
     2. Semantic grounding of the proposed relation in the quote.
     3. Schema constraint compliance (e.g. no cycles in DAGs, symmetric Similarity).
     4. Direction validity.
   - Distinct statuses: `VERIFIED_SUPPORTED`, `INSUFFICIENT_EVIDENCE`, `CONTRADICTED`, `INVALID_DIRECTION`.
5. **Calibrated Relation-Aware Edge Weighting:**
   - Decouple `extraction_confidence`, `evidence_support`, `relation_weight`, and `verification_status`.
   - Relation-appropriate weighting: similarity benefits from embedding/lexical overlap; Application and Part-of require co-occurrence and textual evidence support.
6. **Comprehensive Dual Evaluation:**
   - **Prerequisite:** AL-CPL ground truth (Precision, Recall, F1, NDCG@10, direction accuracy).
   - **Other 4 Relations:** Reference-free automated quality indicators (verbatim grounding rate, verifier agreement, schema compliance, direction validity, duplicate/contradiction rate).
   - **Graph-level topology:** DAG verification, cycle detection, component statistics.
