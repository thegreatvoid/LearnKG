# Deliverable 4: Verified Results Table & Empirical Audit

**Audit Date:** 2026-10-24  
**Project:** LearnKG Comparative Evaluation  
**Evaluation Benchmark:** AL-CPL Basic Geometry ($N = 1,681$ pairs: $524$ positives, $1,157$ negatives)  
**Controlled Evaluation Set:** Common Covered Set ($N = 868$ pairs: $260$ positives, $608$ negatives)

---

## 1. Verified Results Table

The metrics below are verified and traced directly to `data_output/eval_framework/` JSON reports (`prerequisite_report.json`, `weights_report.json`, `concepts_report.json`, `REPORT.md`). All methods in this table are evaluated on the **identical common covered candidate set ($N = 868$)** with 95% bootstrap confidence intervals over 2,000 query resamples.

| Method / Baseline | Concept Count | Benchmark Coverage | Candidate Recall | Edge Precision | Edge Recall | Edge F1 | Closure F1 [95% CI] | ROC-AUC [95% CI] | NDCG@5 | NDCG@10 | P@5 | Measured Runtime | Evaluation Caveats & Boundary Conditions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **Random Baseline** | N/A | N/A | N/A | 0.300 | 0.500 | 0.375 | N/A | 0.500 | 0.511 | 0.607 | 0.399 | < 0.1s | Expected analytical values; NDCG averaged over 20 random tie-breaks. |
| **`rule_v3`** | 130 | 65 / 89 (73.0%) | 0.031 (8 / 260) | 0.875 [0.43, 1.00] | 0.027 [0.01, 0.05] | 0.052 [0.01, 0.10] | 0.052 [0.01, 0.10] | 0.513 [0.50, 0.53] | 0.539 | 0.630 | 0.407 | ~8.4s | Evaluated on common covered set; predicted 8 edges (7 TP, 1 FP); 18 edges unlabelled in AL-CPL; hard-coded lexicon. |
| **`kgx_v2` (Local 7B LLM)** | 204 | 65 / 89 (73.0%) | 0.035 (9 / 260) | 0.444 [0.12, 0.80] | 0.015 [0.00, 0.03] | 0.030 [0.01, 0.06] | 0.037 [0.01, 0.08] | 0.503 [0.49, 0.51] | 0.518 | 0.611 | 0.402 | ~68m | Evaluated on common covered set; predicted 9 edges (4 TP, 5 FP); 46 edges unlabelled in AL-CPL; directional accuracy = 50.0% (chance). |
| **`kgx_v2_hybrid`** | 204 | 65 / 89 (73.0%) | 0.323 (84 / 260) | 0.845 [0.77, 0.91] | 0.273 [0.22, 0.33] | 0.413 [0.35, 0.48] | **0.786 [0.76, 0.81]** | **0.888 [0.85, 0.92]** | **0.881** | **0.906** | **0.670** | ~22s post | Uses reading-order gate (`uses_book_order: true`); evaluation against textbook reading order is **circular**; 432 edges unlabelled in AL-CPL. |
| **Book-Order Baseline** | N/A | 65 / 89 (73.0%) | **1.000 (260 / 260)** | 0.595 [0.55, 0.64] | **0.965 [0.94, 0.98]** | **0.736 [0.70, 0.77]** | Not reported (transitive) | 0.868 [0.81, 0.91] | 0.868 | 0.897 | 0.656 | < 0.5s | Zero-parameter heuristic: $p(A) < p(B)$; continuous score = character gap; puts prerequisite first for 251/260 positives (**96.5% directional accuracy**). |

---

## 2. Weighting & Ranking Ablation Results (AL-CPL Prerequisite Queries)

Evaluated on query concepts in `data_output/eval_framework/weights/weights_report.json` across 2,000 bootstrap resamples:

| Weighting Scheme / Feature | Formula | NDCG@5 [95% CI] | NDCG@10 [95% CI] | $p$-value vs. AHP Baseline | Scientific Interpretation |
|---|---|---|---|---|---|
| **Random Baseline** | Uniform tie-break | 0.483 [0.42, 0.54] | 0.582 [0.52, 0.64] | < 0.001 | Non-informative lower bound. |
| **AHP Baseline** | $0.52S + 0.24C + 0.09P + 0.15E$ | 0.620 [0.55, 0.69] | 0.709 [0.65, 0.76] | Reference | Multi-criteria formula ($CR = 0.022$). |
| **Co-occurrence Only ($C$)** | $1.0 C$ | 0.661 [0.60, 0.72] | **0.723 [0.67, 0.77]** | $p = 0.68$ (Not significant) | Co-occurrence alone achieves identical ranking power to AHP; no multi-factor benefit. |
| **Raw Co-occurrence Count** | Count of co-mentions | 0.682 [0.62, 0.74] | **0.742 [0.69, 0.79]** | $p = 0.31$ (Not significant) | Uncapped co-occurrence count slightly improves ranking. |
| **Definition Overlap ($S$) Only** | $1.0 S$ (Lexical Jaccard) | 0.471 [0.40, 0.55] | **0.589 [0.52, 0.65]** | **$p < 0.001$ (Severe drop)** | Statistically indistinguishable from random baseline (0.582); provides zero discriminative signal. |
| **Chapter Proximity ($P$) Only** | $1.0 P = 1 / (1 + \Delta \text{chap})$ | 0.489 [0.41, 0.56] | **0.605 [0.54, 0.67]** | **$p < 0.001$ (Severe drop)** | Near random ranking. |
| **Section Jaccard ($E$) Only** | $1.0 E$ | 0.598 [0.53, 0.66] | 0.684 [0.63, 0.74] | $p = 0.42$ | Moderate co-mention signal. |
| **Book-Order Gap Alone** | First-mention offset difference | **0.868 [0.81, 0.92]** | **0.891 [0.85, 0.93]** | **$p < 0.0001$ (Dominant)** | Linear presentation order carries massive discriminative ranking utility. |

---

## 3. Audit of Claims in the Existing Manuscript (`paper_conference_revision.tex`)

| Manuscript Statement | Claimed Value in Draft | Verified Value in Artifacts | Audit Verdict | Required Action / Correction |
|---|---|---|---|---|
| `rule_v3` Prerequisite Edge F1 & AUC | $F_1 = 0.052$, $\text{AUC} = 0.513$ | $F_1 = 0.0520$, $\text{AUC} = 0.5126$ | **[VERIFIED]** | Retain exact numbers; note denominator (8 pairs decided). |
| `kgx_v2` Prerequisite Edge F1 & AUC | $F_1 = 0.030$, $\text{AUC} = 0.503$ | $F_1 = 0.0296$, $\text{AUC} = 0.5029$ | **[VERIFIED]** | Retain exact numbers; emphasize 95% CI encompasses 0.50 (chance). |
| `kgx_v2_hybrid` Closure F1 & AUC | Closure $F_1 = 0.786$, $\text{AUC} = 0.888$ | Closure $F_1 = 0.7858$, $\text{AUC} = 0.8876$ | **[VERIFIED-WITH-QUALIFICATION]** | Must flag that high AUC is driven by the structural forward gate (`gap > 0`), which is circular when evaluated against textbook order. |
| Book-Order Baseline F1 & AUC | $F_1 = 0.736$, $\text{AUC} = 0.868$ | $F_1 = 0.7361$, $\text{AUC} = 0.8679$ | **[VERIFIED]** | Highlight as primary empirical baseline: 96.5% directional accuracy (251/260). |
| Concept Overlap & AL-CPL Matching | 130 concepts (`rule_v3`), 204 (`kgx_v2`), 65 matched in AL-CPL | 130 nodes, 204 nodes, 65 matched | **[VERIFIED]** | Correctly explains that 13 missing concepts are absent from textbook text. |
| AHP NDCG@10 vs. Co-occurrence alone | AHP = 0.709, Co-occurrence = 0.723 | AHP = 0.7088, $C = 0.7231$ | **[VERIFIED]** | Retain as empirical ablation showing Saaty multi-factor weighting is redundant. |
| Book-Order NDCG@10 | NDCG@10 = 0.891 | NDCG@10 = 0.8912 | **[VERIFIED]** | Demonstrates the strength of the linear presentation prior. |
| "Pipeline successfully detects student knowledge gaps" | P@5: Rule 0.073, LLM 0.047, BookOrder 0.455 | Graph traversal retrieval scores verified | **[CORRECTION-REQUIRED]** | This is a *structural retrieval proxy* (finding ancestors of masked leaves), NOT a validated study on human students or cognitive diagnostics. Must rename to "Prerequisite Retrieval as a Structural Proxy". |
