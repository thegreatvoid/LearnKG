# Independent Reviewer Assessment: Rigorous Evaluation Report

**Review Date:** 2026-10-23  
**Submission Title:** Evaluating Local Large Language Models for Educational Prerequisite Extraction: The Surprising Dominance of Structural Reading-Order Priors  
**Target Venue:** Conference on Empirical AI / Semantic Web / Educational Data Mining (e.g., ESWC, ISWC, EDM)  
**Track:** Research / Evaluation Paper  
**Simulated Decision:** **Strong Accept (Short Paper) / Weak Accept (Full Paper pending multi-domain replication)**

---

## 1. Summary of the Work
The paper conducts a controlled empirical evaluation of local open-weight LLMs (\texttt{Qwen-2.5-7B}) for constructing educational knowledge graphs from a high-school geometry textbook (*CK-12 Basic Geometry*). Evaluated against the human-annotated AL-CPL Geometry benchmark ($N=1,681$ pairs, common covered set $N=868$), the authors demonstrate that an unconstrained 7B model operates near chance for directional prerequisite extraction ($\text{ROC-AUC} = 0.503$, directional accuracy $50.0\%$). In contrast, a zero-parameter book-order baseline achieves an $F_1$ of $0.736$, an ROC-AUC of $0.868$, and $96.5\%$ directional accuracy. The authors trace the pipeline cascade to prove that candidate-pair generation is the dominant bottleneck, and ablate the Saaty Analytic Hierarchy Process (AHP) formula to show that sentence co-occurrence alone accounts for its ranking efficacy.

---

## 2. Detailed Review Criteria

### Criterion A: Scientific Contribution & Novelty
- **Strengths:** 
  1. The paper provides a valuable, refreshing reality check against inflated expectations of local LLM capabilities. The demonstration that a simple 5-line reading-order heuristic outperforms a 7B parameter neural model by over $0.70$ points in $F_1$ is a compelling and publishable empirical result.
  2. The decomposition of recall loss across the 5 pipeline stages is exceptionally well executed. Many KG papers simply report low end-to-end recall; this paper proves mathematically that $43\%$ of valid pairs are discarded before the LLM is ever called.
  3. The ablation of the Saaty AHP weighting formula exposes a crucial insight: complex multi-criteria formulas can masquerade as sophisticated while deriving their entire predictive signal from simple co-occurrence.
- **Weaknesses:**
  1. The core empirical findings currently rest on a single textbook domain (*CK-12 Basic Geometry*). While the authors acknowledge this limitation openly, cross-domain validation (e.g., Physics) is necessary to prove universality.

### Criterion B: Technical Soundness & Methodology
- **Strengths:**
  1. Methodological hygiene is exemplary. The evaluation enforces strict directionality (no bidirectional credit inflation), uses a common covered set ($N=868$) to prevent unfair baselines, and computes 95\% bootstrap confidence intervals clustered over query concepts.
  2. The authors explicitly flag circularity: because the hybrid pipeline uses reading order in its construction, they do not present its directional consistency with reading order as independent evidence.
  3. The codebase contains a rigorous suite of unit and regression tests (`test_framework.py`, `test_kg_extract.py`) that verify metric calculations and edge cases.
- **Weaknesses:**
  1. The four non-prerequisite relation types (Part-of, Application, Extension, Similarity) lack external ground truth. The reference-free diagnostics provide useful qualitative clues, but cannot replace human-annotated precision/recall.

### Criterion C: Presentation and Clarity
- **Strengths:**
  1. The LaTeX manuscript is well-written, dense with empirical data, and avoids promotional hyperbole.
  2. Tables are informative, complete with denominators, confidence intervals, and significance values.
- **Weaknesses:**
  1. The distinction between concept-level prerequisite retrieval and true student "knowledge-gap detection" was initially blurred; the authors have properly corrected this to a structural proxy task.

---

## 3. Reviewer Checklist & Recommendations

| Item | Assessment | Notes |
|---|---|---|
| Is the empirical evidence reproducible? | **Yes** | Deterministic scripts and JSON logs verified. |
| Are statistical tests appropriate? | **Yes** | Clustered bootstrap over concepts + sign-flip permutation tests. |
| Are baselines competitive? | **Yes** | Random, Rule, LLM, Structural, and Hybrid all tested on identical pairs. |
| Is the claim scope justified? | **Yes** | Claims restricted strictly to the evaluated model and corpus. |

### Required Action Items for Main Track Submission:
1. Complete the pending **Second-Domain Replication** on *OpenStax Physics* using the frozen protocol in `second_domain_protocol.md`.
2. Run the pending **Multi-Model Scaling Matrix** (evaluating 3B and 14B models on the exact candidate set) to confirm whether directional chance performance is an artifact of 7B parameter capacity.
3. Complete the double-annotation of the 378-item package to establish ground-truth metrics for the remaining 4 relation types.
