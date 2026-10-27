# Research Audit: Repository and Evidence Verification

**Date:** 2026-10-23  
**Project:** LearnKG (Multi-Relation Educational Knowledge Graph Construction and Evaluation)  
**Corpus / Domain:** CK-12 Basic Geometry (`data_input/ck12_geometry/ck12_basic_geometry_concepts.txt`)  
**External Benchmark:** AL-CPL Geometry (Liang et al., 2015 / AAAI 2018)  
**Status:** Phase One Complete (Strict Evidence Traceability)

---

## 1. Executive Inventory

The repository contains three distinct generations of pipelines and a unified evaluation framework:

1. **`educational_pipeline` (`rule_v3` / `rule_2026-10-11`):**
   - Heuristic and rule-based extraction.
   - Text segmentation with structure detection (`parser.py`, `chunker.py`, `structure_detector.py`).
   - Hard-coded textbook vocabulary (`ck12_basic_geometry_concepts.txt`) and regex-based noun phrase candidate extraction.
   - Connective and cue-word relation extraction (`relation_extractor.py`) across 5 relation types: *Prerequisite*, *Part-of*, *Application*, *Extension*, *Similarity*.
   - Saaty Analytic Hierarchy Process (AHP) edge weighting ($W = 0.52 S + 0.24 C + 0.09 P + 0.15 E$).

2. **`kg_extract` (`kgx_v2`):**
   - Grounded LLM-based extraction using open-weight models (`qwen2.5:7b-instruct` / `qwen2.5:3b-instruct` via Ollama).
   - Unsupervised candidate concept extraction with noun-phrase filtering and verbatim text grounding (`concepts.py`).
   - Candidate pair generation via sentence co-occurrence, chunk co-occurrence, and embedding nearest neighbors (`pairs.py`).
   - Relation classification with order-swap debiasing and multi-class prompt scoring (`score.py`).
   - Enforces DAG consistency on Prerequisite relations (`consistency.py`).

3. **`kgx_v2_hybrid`:**
   - Neuro-symbolic synthesis combining LLM relatedness with reading-order gating (`hybrid.py`).
   - Composite scoring: $\text{forward\_gate} \times \text{mean}(\text{rank}(\text{gap}), \text{rank}(\text{cooc}), \text{rank}(\text{RefD}), \text{rank}(\text{LLM\_rel}))$.
   - Explicitly sets `uses_book_order: true` in `run_meta.json`.

4. **`kg_eval` & `kg_eval.framework`:**
   - Standardized evaluation suite comparing all KGs against AL-CPL ground truth on common covered concept pairs (868 pairs).
   - Automated reference-free structural diagnostics (`relation_checks.py`), ranking metrics with 95% bootstrap CIs (`weights_eval.py`, `prereq_eval.py`), textual grounding distance via BIGS (`bigs.py`), and a 378-item blinded multi-relation annotation package (`annotation_kit.py`).

---

## 2. Evidence Traceability Table

Every empirical claim reported in the existing manuscript (`learnkg_evaluation_paper.tex`) has been traced to its generating script and machine-readable output:

| Manuscript Claim / Metric | Value in Paper | Source Artifact | Generating Script | Verified? | Notes & Audit Status |
|---|---|---|---|---|---|
| AL-CPL Gold Set Size | 1,681 pairs (524 pos, 1,157 neg) | `data_input/ck12_geometry/geometry.pairs` | `kg_eval.data.load_alcpl()` | **Verified** | Standard benchmark dataset. |
| AL-CPL Concept Matching | 65 / 89 concepts (73.0%) | `data_output/eval_framework/concepts/concepts_report.json` | `kg_eval.framework.concepts_eval` | **Verified** | 13 absent from book; 11 missed by extractor. |
| Common Covered Evaluated Pairs | 868 pairs (260 pos, 608 neg) | `data_output/eval_framework/prerequisite/prereq_eval_report.json` | `kg_eval.framework.prereq_eval` | **Verified** | Exact pairs where both source and target are in all 4 KGs. |
| `rule_v3` Prerequisite Edge P/R/F1 | 0.875 / 0.027 / 0.052 | `prereq_eval_report.json:15` | `kg_eval.framework.prereq_eval` | **Verified** | Evaluated on common covered set (7/8 correct). |
| `rule_v3` Closure F1 [95% CI] | 0.052 [0.01, 0.10] | `prereq_eval_report.json:16` | `kg_eval.framework.prereq_eval` | **Verified** | Transitive closure reachability over DAG. |
| `rule_v3` ROC-AUC [95% CI] | 0.513 [0.50, 0.53] | `prereq_eval_report.json:18` | `kg_eval.framework.prereq_eval` | **Verified** | Operating essentially at chance. |
| `kgx_v2` Prerequisite Edge P/R/F1 | 0.444 / 0.015 / 0.030 | `prereq_eval_report.json:28` | `kg_eval.framework.prereq_eval` | **Verified** | 4/9 edges correct on common covered set. |
| `kgx_v2` Closure F1 [95% CI] | 0.037 [0.01, 0.08] | `prereq_eval_report.json:29` | `kg_eval.framework.prereq_eval` | **Verified** | Very sparse reachability. |
| `kgx_v2` ROC-AUC [95% CI] | 0.503 [0.49, 0.51] | `prereq_eval_report.json:31` | `kg_eval.framework.prereq_eval` | **Verified** | 95% CI encompasses 0.50 (exact chance). |
| `kgx_v2_hybrid` Edge P/R/F1 | 0.845 / 0.273 / 0.413 | `prereq_eval_report.json:41` | `kg_eval.framework.prereq_eval` | **Verified** | Direct edges on covered set. |
| `kgx_v2_hybrid` Closure F1 [95% CI] | 0.786 [0.76, 0.81] | `prereq_eval_report.json:42` | `kg_eval.framework.prereq_eval` | **Verified** | Strong boost due to structural transitive paths. |
| `kgx_v2_hybrid` ROC-AUC [95% CI] | 0.888 [0.85, 0.92] | `prereq_eval_report.json:44` | `kg_eval.framework.prereq_eval` | **Verified** | Substantial ranking discrimination. |
| Book-Order Baseline P/R/F1 | 0.595 / 0.965 / 0.736 | `prereq_eval_report.json:54` | `kg_eval.framework.prereq_eval` | **Verified** | Zero-parameter reading order baseline. |
| Book-Order Baseline ROC-AUC | 0.868 [0.81, 0.91] | `prereq_eval_report.json:56` | `kg_eval.framework.prereq_eval` | **Verified** | Position gap $p(A) - p(B)$. |
| Directional Accuracy: Book Order | 251 / 260 correct (96.5%) | `prereq_eval_report.json:57` | `kg_eval.framework.prereq_eval` | **Verified** | Ground-truth prerequisites appear earlier in text. |
| Directional Accuracy: `kgx_v2` | 4 / 8 correct (50.0%) | `prereq_eval_report.json:33` | `kg_eval.framework.prereq_eval` | **Verified** | LLM direction classification operates at chance. |
| Directional Accuracy: `rule_v3` | 7 / 7 correct (100.0%) | `prereq_eval_report.json:20` | `kg_eval.framework.prereq_eval` | **Verified** | Only 7 pairs predicted; all 7 were forward. |
| Saaty AHP Consistency Ratio ($CR$) | $CR = 0.022 < 0.10$ | `docs/ahp_weights.md:42` | Calculated from matrix | **Verified** | Eigenvalue analysis verified mathematically. |
| Weight Ranking: AHP NDCG@10 | 0.709 [0.65, 0.76] | `weights_eval_report.json:12` | `kg_eval.framework.weights_eval`| **Verified** | Paired query ranking on AL-CPL. |
| Weight Ranking: Co-occurrence alone | 0.723 [0.67, 0.77] | `weights_eval_report.json:18` | `kg_eval.framework.weights_eval`| **Verified** | Statistically indistinguishable from AHP ($p=0.68$). |
| Weight Ranking: Definition overlap ($S$)| 0.589 [0.52, 0.65] | `weights_eval_report.json:24` | `kg_eval.framework.weights_eval`| **Verified** | No better than random ranking ($p < 0.001$). |
| Weight Ranking: Book Order alone | 0.891 [0.85, 0.93] | `weights_eval_report.json:30` | `kg_eval.framework.weights_eval`| **Verified** | Massive predictive edge from reading order. |
| Concept-level Gap Detection Proxy | P@5: Rule 0.073, LLM 0.047, BookOrder 0.455 | `gap_proxy_report.json` | `kg_eval.framework.gap_proxy` | **Verified** | Concept-level retrieval of missing prerequisites. |
| Multi-relation Annotation Package | 378 items (blinded, stratified) | `data_output/eval_framework/annotation/` | `kg_eval.framework.annotation_kit` | **Verified** | Sampling verified; independent double annotation pending. |

---

## 3. Methodological and Experimental Risks Identified

1. **Single Domain / Single Book Confinement:**
   - All empirical results currently derive exclusively from *CK-12 Basic Geometry*.
   - Without the planned second-domain replication (*OpenStax Physics* + AL-CPL Physics), the manuscript cannot claim that findings generalize across educational textbooks.

2. **Single Model Scale (7B) in Main Runs:**
   - The LLM pipeline evaluates `qwen2.5:7b-instruct`.
   - The paper currently conjectures that small parameter scale causes directional confusion, but has not yet proven scaling behavior against 3B or 14B models on the exact candidate set.

3. **Candidate Generation Bottleneck vs. Classification Bottleneck:**
   - Candidate generator proposes 989 pairs in `kgx_v2` out of tens of thousands possible pairs.
   - It covers only 65 of 89 concepts. The recall ceiling imposed by candidate generation must be explicitly separated from relation classification error.

4. **Circular Evaluation Risk for Hybrid KG:**
   - `kgx_v2_hybrid` scores pairs using `gap > 0` (book order). Evaluating its prerequisite direction against book order is trivially circular. The evaluation suite already flags this, and the manuscript must maintain this rigorous distinction.

5. **Proxy Task vs. Downstream Application:**
   - Section 8 of the evaluation tests prerequisite retrieval from leaf concepts, termed "gap proxy". The paper must clarify that this is an information retrieval abstraction, not a validated study on human student learning outcomes.
