# Deliverable 1: Implementation Inventory of Methodologies in LearnKG

**Audit Date:** 2026-10-24  
**Auditor:** Senior AI Researcher & Knowledge Graph Evaluation Specialist  
**Target Repository:** `/home/dino/finyr/LearnKG`

---

## 1. Executive Summary: The "Five Methodologies" Reality Check

A critical inspection of the repository reveals that the project **does not contain five independent, end-to-end knowledge graph construction methodologies**.

Instead, the codebase contains:
- **Two genuine end-to-end extraction pipelines:**
  1. `rule_v3` (heuristic/symbolic pattern extraction with hard-coded textbook lexicon and AHP scoring in `educational_pipeline/`).
  2. `kgx_v2` (grounded open-weight LLM extraction with unsupervised noun-phrase filtering and swap-sampling in `kg_extract/`).
- **One post-processing neuro-symbolic synthesizer:**
  3. `kgx_v2_hybrid` (takes `kgx_v2` concept nodes and LLM relatedness scores, then applies a structural textbook reading-order gate, RefD statistical metrics, and greedy DAG cycle elimination in `kg_extract/hybrid.py`).
- **Two structural / ranking baselines (not independent graph constructors):**
  4. **Zero-Parameter Reading-Order Baseline** ($p(A) < p(B) \implies A \to B$, implemented in `kg_eval/framework/prereq_eval.py` and `kg_eval/book_order.py`).
  5. **Edge Weighting & Scoring Functions** (Saaty AHP formula vs. Co-occurrence alone vs. Lexical Definition overlap, implemented in `educational_pipeline/relation_extractor.py` and evaluated in `kg_eval/framework/weights_eval.py`).

Claiming that these represent "five independent knowledge graph construction systems" would immediately trigger a desk rejection or severe reviewer skepticism at venues like ESWC, ISWC, EDM, or AIED. The paper must explicitly separate:
1. **The Construction Pipelines** (`rule_v3`, `kgx_v2`, `kgx_v2_hybrid`).
2. **The Structural Inductive Baselines** (Reading Order, Random Guessing).
3. **The Ranking & Scoring Ablations** (AHP vs. Co-occurrence vs. Definition overlap).

---

## 2. Methodology Inventory Table

| Method / System | Actual Implementation Status | Exact Source Files | Inputs | Outputs | Execution / Test Status | Reproducible from Artifacts? |
|---|---|---|---|---|---|---|
| **1. Rule-Based Pipeline (`rule_v3`)** | **Full end-to-end pipeline:** Text segmentation, structure detection, regex pattern matching, pedagogical rules, Saaty AHP scoring. | `educational_pipeline/parser.py`<br>`educational_pipeline/chunker.py`<br>`educational_pipeline/concept_extractor.py`<br>`educational_pipeline/relation_extractor.py`<br>`educational_pipeline/pipeline.py` | Raw textbook text (`.txt`/`.pdf`), hard-coded geometry vocabulary (`ck12_basic_geometry_concepts.txt`), relation schema YAML. | `concepts.csv` (130 nodes), `relations.csv` (84 edges: 27 prereq, 7 part-of, 2 app, 46 sim, 2 ext), Pyvis HTML graph. | **Implemented & Tested** across test suite (`test_educational_pipeline.py`). | **Yes.** Verifiable in `data_output/baseline_v3/` and `data_output/eval_framework/prerequisite/pairs_rule_v3.csv`. |
| **2. Standalone Local LLM (`kgx_v2`)** | **Full end-to-end pipeline:** Unsupervised noun phrase discovery, Ollama LLM prompting with order-swap debiasing, candidate pair generation, DAG pruning. | `kg_extract/text.py`<br>`kg_extract/concepts.py`<br>`kg_extract/pairs.py`<br>`kg_extract/score.py`<br>`kg_extract/backend.py`<br>`kg_extract/consistency.py`<br>`kg_extract/run.py` | Raw textbook text, Ollama local model (`qwen2.5:7b-instruct` or `qwen2.5:3b-instruct`). | `concepts.csv` (204 nodes), `pair_scores.csv` (3,001 scored pairs), `relations.csv` (545 edges: 54 prereq, 216 part-of, 228 app, 4 sim, 43 ext). | **Implemented & Tested** (`kg_extract/test_kg_extract.py`). | **Yes.** Verifiable in `data_output/ck12_geometry_kgx_v2/` and evaluation report logs. |
| **3. Neuro-Symbolic Hybrid (`kgx_v2_hybrid`)** | **Post-processing synthesis:** Fuses `kgx_v2` LLM relatedness with forward reading-order gate, RefD statistical metrics, sentence co-occurrence, and DAG cycle removal. | `kg_extract/hybrid.py`<br>`kg_extract/consistency.py` | `kgx_v2/concepts.csv`, `kgx_v2/pair_scores.csv`, raw source text. | `concepts.csv` (204 nodes), `pair_scores.csv` (41,413 pairs), `relations.csv` (669 edges: 518 prereq, 71 part-of, 63 app, 1 sim, 16 ext). | **Implemented & Tested.** | **Yes.** Verifiable in `data_output/ck12_geometry_kgx_v2_hybrid/` and `prerequisite_report.json`. |
| **4. Structural Reading-Order Baseline** | **Zero-parameter structural baseline:** Predicts prerequisite dependency purely based on first appearance in textbook ($p(A) < p(B) \implies A \to B$). | `kg_eval/book_order.py`<br>`kg_eval/framework/prereq_eval.py` | Concept first-mention character offsets in source textbook, evaluation pair list. | Continuous score = position gap $p(B) - p(A)$; binary classification = $p(A) < p(B)$. | **Implemented & Tested.** Evaluated on all AL-CPL candidate pairs. | **Yes.** Output logged in `data_output/eval_framework/prerequisite/prerequisite_report.json`. |
| **5. Edge-Weighting / Ranking Functions (AHP & Ablations)** | **Scoring & Ranking module:** Saaty Analytic Hierarchy Process ($W = 0.52S + 0.24C + 0.09P + 0.15E$) vs. Co-occurrence alone ($C$) vs. Lexical Definition overlap ($S$). | `educational_pipeline/relation_extractor.py`<br>`kg_eval/framework/weights_eval.py`<br>`docs/ahp_weights.md` | Grounded definitions, sentence co-occurrence counts, chapter numbers, section sets. | Normalized scalar weights $[0, 1]$ per relation edge; NDCG ranking logs. | **Implemented & Tested.** Paired bootstrap evaluations on AL-CPL queries. | **Yes.** Fully documented in `data_output/eval_framework/weights/weights_report.json`. |
| **Alternative: Neural Prerequisite Classifier** | Supervised cross-encoder / BERT pairwise classifier. | `educational_pipeline/neural_prerequisite_extractor.py`<br>`evaluate_prerequisite_extraction.py` | Concept definition pairs, pretrained transformer embeddings. | Pairwise prerequisite probability $[0, 1]$. | **Partially Implemented / Legacy.** Not part of main `kg_eval.framework` frozen benchmark. | **Partial.** Exists in older scripts, superseded by `kg_extract`. |
| **Second-Domain Replication (Physics)** | Cross-domain generalization to OpenStax Physics. | `second_domain_protocol.md` | OpenStax Physics text, AL-CPL Physics benchmark pairs. | Cross-domain evaluation tables. | **Proposed / Protocol Frozen.** Code exists conceptually; full execution pending. | **Not Yet Reproducible** (awaiting execution). |
| **Multi-Model Scaling Matrix (3B vs 7B vs 14B)** | Controlled parameter scaling on identical candidate set. | Manuscript §6 [TODO], `experiment_plan.md` | Ollama model checkpoints (3B, 7B, 14B). | Comparative ROC-AUC and F1 across model scales. | **Proposed / Pending.** Early exploratory runs exist (`run1`, `run2`), but controlled frozen matrix is unexecuted. | **Not Yet Reproducible.** |
| **Multi-Relation Human Annotation** | Double-annotation of 378 sampled items across 5 relations. | `kg_eval/framework/annotation_kit.py`<br>`data_output/eval_framework/annotation/` | 378 sampled edges across 4 KGs. | Cohen's Kappa, adjudicated ground truth for 4 non-prereq types. | **Prepared.** Kit generated; human adjudication pending. | **Kit Reproducible; Adjudication Pending.** |
