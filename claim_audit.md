# Claim Audit: Systematic Verification of Scientific Claims

**Date:** 2026-10-23  
**Target Manuscript:** `learnkg_evaluation_paper.tex`  
**Evaluation Scope:** Truthfulness, precision of language, empirical support, and required corrections.

---

## 1. Classification Framework

Every claim in the manuscript is audited and classified into one of six categories:
- **[SUPPORTED]**: Directly established by verified experimental data and reproducible code.
- **[SUPPORTED-WITH-QUALIFICATION]**: Empirically true on this specific dataset, but requires explicit boundary conditions or narrower wording.
- **[UNVERIFIED-ASSUMPTION]**: Stated as an explanation or fact, but represents an untested hypothesis.
- **[PENDING-EXPERIMENT]**: Marked as `[TODO]` or dependent on pending experiments (e.g., second domain, multi-model scaling).
- **[UNSUPPORTED/OVERSTATED]**: Generalization or framing that exceeds what the empirical data proves.
- **[CORRECTION-REQUIRED]**: Wording that conflates distinct tasks (e.g., calling prerequisite retrieval "knowledge gap detection").

---

## 2. Systematic Audit of Manuscript Claims

### Claim 1: "Standalone local LLMs perform near chance on educational prerequisite extraction."
- **Classification:** **[SUPPORTED-WITH-QUALIFICATION]**
- **Supporting Evidence:** In `data_output/eval_framework/prerequisite/prereq_eval_report.json`, `kgx_v2` achieves ROC-AUC = 0.503 [95% CI: 0.49, 0.51] and edge F1 = 0.030 on the common covered AL-CPL evaluation set. Directional accuracy on positive pairs is 4/8 (50.0%).
- **Qualification Required:** This holds for `qwen2.5:7b-instruct` operating in zero/few-shot prompt classification on expository textbook text without structural reading-order features. It should not be generalized to all local LLMs or all possible prompting strategies without the multi-model and second-domain data.

### Claim 2: "A zero-parameter book-order baseline substantially outperforms the 7B LLM."
- **Classification:** **[SUPPORTED]**
- **Supporting Evidence:** The simple first-mention reading order heuristic ($p(A) < p(B) \implies A \to B$) achieves F1 = 0.736, ROC-AUC = 0.868 [95% CI: 0.81, 0.91], and 251/260 (96.5%) directional accuracy on the exact same common covered set.
- **Required Action:** Keep this as a primary finding, but emphasize the theoretical reason: educational textbooks are pedagogically organized to teach dependencies before advanced material ("temporal presentation prior").

### Claim 3: "The neuro-symbolic hybrid achieves the highest prerequisite F1 and closure scores."
- **Classification:** **[SUPPORTED-WITH-QUALIFICATION]**
- **Supporting Evidence:** `kgx_v2_hybrid` reaches direct-edge F1 = 0.413, closure F1 = 0.786 [95% CI: 0.76, 0.81], and ROC-AUC = 0.888 [95% CI: 0.85, 0.92].
- **Qualification Required:** The paper must explicitly reiterate that `kgx_v2_hybrid` achieves this primarily by using the reading-order forward gate (`gap > 0`). Evaluating its prerequisite direction against book order is circular (`uses_book_order: true`), and the LLM's marginal contribution over book order alone is modest (AUC 0.888 vs 0.868).

### Claim 4: "Definition lexical overlap ($S$) provides no discriminative signal for ranking prerequisites."
- **Classification:** **[SUPPORTED]**
- **Supporting Evidence:** In `data_output/eval_framework/weights/weights_eval_report.json`, using $S$ alone yields NDCG@10 = 0.589 [95% CI: 0.52, 0.65], which is statistically indistinguishable from a random tie-break baseline (0.577, $p = 0.53$). Co-occurrence ($C$) alone achieves NDCG@10 = 0.723 ($p < 0.001$ over $S$).
- **Required Action:** Retain this finding as an empirical critique of the Saaty AHP formula ($W = 0.52S + 0.24C + 0.09P + 0.15E$), where the heaviest-weighted term ($0.52 S$) contributes the least discriminative utility.

### Claim 5: "The pipeline successfully detects student knowledge gaps."
- **Classification:** **[CORRECTION-REQUIRED]**
- **Supporting Evidence:** The evaluation in `gap_proxy.py` simulates knowledge gaps by masking leaf concepts in the graph and computing P@5/NDCG retrieval against AL-CPL ancestors. No human student assessments, cognitive diagnostics, or learning log data were evaluated.
- **Required Correction:** The paper must rename this task: **"Prerequisite Retrieval as a Structural Proxy for Knowledge Gap Tracing"**, and explicitly document that real pedagogical gap detection requires learner interaction data.

### Claim 6: "The 5-relation ontology suffers from taxonomic vs. meronymic confusion."
- **Classification:** **[SUPPORTED]**
- **Supporting Evidence:** Audited in `educational_pipeline/relation_extractor.py` and `kg_extract/score.py`. The "Part-of" prompt and pattern lists explicitly included phrases like `"is a type of"` and `"special case of"`, confounding hyponymy (is-a) with meronymy (part-of). Automatic contradiction diagnostics in `relation_checks.py` identified 43 semantic type conflicts.
- **Required Action:** Highlight this in the ontology and error analysis sections as a key engineering and schema lesson for educational knowledge graph construction.

### Claim 7: "Local LLM capability scales with parameter size (3B vs 7B vs 14B)."
- **Classification:** **[PENDING-EXPERIMENT]**
- **Supporting Evidence:** Currently marked as `[TODO]` in the LaTeX draft. While initial 3B runs were explored in early development (`kg_extract_run1`), a clean, controlled multi-model matrix on identical candidate pairs has not yet been executed in the frozen framework.
- **Required Action:** Keep clearly demarcated as a pending ablation or future work if local compute constraints prevent running 14B inference during this revision.

### Claim 8: "The findings generalize across STEM textbooks."
- **Classification:** **[PENDING-EXPERIMENT / UNSUPPORTED]**
- **Supporting Evidence:** Currently evaluated exclusively on CK-12 Basic Geometry. The second-domain protocol (`second_domain_protocol.md`) for OpenStax Physics is documented, but the experiment has not been executed.
- **Required Action:** Confine the empirical claims strictly to CK-12 Geometry and explicitly discuss single-domain confinement under Threats to Validity (External Validity).
