# Deliverable 9: Recommended Paper Direction & Contribution Blueprint

**Audit Date:** 2026-10-24  
**Project:** LearnKG Publication Blueprint  
**Auditor:** Senior AI Researcher & Academic Publication Strategist

---

## 1. The Recommended Directions

### Primary Recommended Direction: Focused Empirical Evaluation Paper (Short / Research Track)
* **Target Venues:** **EDM (Educational Data Mining)**, **AIED (Artificial Intelligence in Education)**, **ESWC (Extended Semantic Web Conference - Research/Resources Track)**, or **ACL/EMNLP Findings (Evaluation Track)**.
* **Format:** 4 to 6 pages (plus references).
* **Rationale:** You already possess 100% of the verified, machine-readable empirical results needed for this paper. The narrative is tight, counter-intuitive, scientifically honest, and methodologically irreproachable. It avoids the delays of long-running GPU training or human annotation campaigns.

### Fallback Direction: Full Comparative & Cross-Domain Study (Full Paper Track)
* **Target Venues:** **IEEE Transactions on Learning Technologies (TLT)**, **International Semantic Web Conference (ISWC - Research Track)**, or **Computers & Education: Artificial Intelligence**.
* **Format:** 8 to 12 pages.
* **Requirement to Trigger Fallback:** Must execute the frozen `second_domain_protocol.md` on OpenStax Physics with AL-CPL Physics to replicate the reading-order vs. LLM findings across two distinct STEM disciplines.

---

## 2. Recommended Working Title & Precise Research Question

* **Recommended Working Title:**  
  $$\textbf{Evaluating Local Large Language Models for Educational Prerequisite Extraction:}$$  
  $$\textbf{The Surprising Dominance of Structural Reading-Order Priors}$$

* **Alternative Title (if emphasizing multi-method comparison):**  
  $$\textbf{Beyond Chronology: A Rigorous Comparative Benchmark of Heuristic, Neural,}$$  
  $$\textbf{and Structural Approaches to Educational Knowledge Graph Construction}$$

* **Primary Research Question (Central Thesis):**  
  *Do locally deployable open-weight LLMs (sub-10B parameters) reliably discern directional pedagogical dependencies directly from textbook prose, or does sequential presentation order (reading-order prior) account for the observed predictive accuracy in automated educational knowledge graph construction?*

---

## 3. Four Core Scientific Contributions

1. **A Controlled Forensic Evaluation of Local LLMs vs. Structural Priors:**  
   We demonstrate that an unconstrained open-weight 7B parameter model (`Qwen-2.5-7B`) operating on expository textbook text performs near chance for directional prerequisite extraction ($\text{ROC-AUC} = 0.503$, directional accuracy $50.0\%$). In contrast, a zero-parameter reading-order baseline achieves an $F_1$ of $0.736$, an ROC-AUC of $0.868$, and $96.5\%$ directional accuracy on the identical benchmark set ($N=868$).

2. **Pipeline Recall Bottleneck Decomposition:**  
   We formally deconstruct the recall cascade across the entire knowledge graph pipeline, proving that candidate-pair generation (sparse intra-sentence and chunk co-occurrence) constitutes the primary structural bottleneck, discarding over $43\%$ of reachable benchmark dependencies before classification begins.

3. **Empirical Deconstruction of Multi-Criteria Edge Weighting:**  
   We audit Saaty's Analytic Hierarchy Process (AHP) formulation ($CR = 0.022$), showing that its ranking efficacy ($NDCG@10 = 0.709$) is driven entirely by simple sentence co-occurrence ($NDCG@10 = 0.723$), while lexical definition overlap contributes zero discriminative utility ($NDCG@10 = 0.589$ vs. random $0.582$, $p < 0.001$).

4. **Reference-Free Multi-Relation Diagnostic Suite & Open Benchmark Kit:**  
   We provide a reusable diagnostic protocol that detects taxonomic vs. meronymic category errors (*is-a* vs. *part-of*) and release a 378-item blinded multi-relation annotation package alongside an end-to-end reproducible evaluation framework.

---

## 4. Experiment Categorization

### Essential Experiments (Included in Submission Draft)
- **E1:** Controlled Prerequisite Benchmark on Common Covered AL-CPL Pairs ($N=868$).
- **E2:** Recall Cascade Decomposition across the 5 pipeline stages.
- **E3:** Neuro-Symbolic Hybrid vs. Reading Order Ablation.
- **E4:** Saaty AHP vs. Single-Factor Ranking Ablation (NDCG@k).
- **E5:** Reference-Free Multi-Relation Contradiction and Schema Audit.
- **E6:** Prerequisite Retrieval as a Structural Proxy for Gap Tracing.

### Optional Experiments (Marked as Demarcated Future Work)
- **E7:** Multi-Model Parameter Scaling (3B vs. 7B vs. 14B) on identical candidate pairs.
- **E8:** Second-Domain Replication on OpenStax Physics.
- **E9:** Dual-Annotator Agreement on the 378-item blinded package.

---

## 5. Main Scientific Risks & Mitigation Strategy

| Scientific Risk | Severity | Reviewer Impact | Mitigation Strategy Implemented in Paper |
|---|---|---|---|
| **Single-Textbook Confinement** | Moderate | May prompt request for multi-domain validation. | Explicitly bound claim scope: title specifies *"Educational Prerequisite Extraction"*, abstract highlights CK-12 Geometry, and second-domain protocol is frozen and published in repository. |
| **Circularity Critique of Hybrid System** | High | Accusation that hybrid claims false neural success. | Explicitly flag `uses_book_order: true` in run metadata; report that directional accuracy ($96.5\%$) derives from the forward gate, not emergent LLM cognition. |
| **Misrepresenting Heuristic Proxy as Student Cognitive Assessment** | High | Severe pushback from educational psychologists. | Strike all phrases claiming "student knowledge-gap detection". Restrict terminology strictly to *"Prerequisite Retrieval as a Structural Proxy for Curricular Tracing"*. |
| **Lack of Non-Prerequisite Ground Truth** | Low to Moderate | AL-CPL only evaluates prerequisites. | Frame the other 4 relations honestly under *Exploratory Diagnostics and Reference-Free Consistency Checks*. |

---

## 6. Minimum Completion Criteria Before Submission

1. Ensure all numbers in the LaTeX manuscript match `data_output/eval_framework/REPORT.md`.
2. Keep the unified Table 1 formatted with denominators, 95% CIs, and explicit circularity footnotes.
3. Package the evaluation suite with `REPRODUCING.md` so reviewers can verify all JSON reports in one command (`python3 -m kg_eval.framework.run_all`).
