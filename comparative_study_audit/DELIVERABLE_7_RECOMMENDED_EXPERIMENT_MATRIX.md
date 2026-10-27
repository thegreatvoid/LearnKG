# Deliverable 7: Recommended Experiment Matrix (E1 to E12)

**Audit Date:** 2026-10-24  
**Project:** LearnKG Comparative Evaluation  
**Auditor:** Senior AI Researcher & Knowledge Graph Evaluation Specialist

---

## 1. Classification Overview

To prevent the paper from becoming an unmanageably broad or bloated engineering report, the twelve candidate experiments are divided strictly into:
- **Core Essential Experiments (E1 to E6):** Necessary and sufficient to support a top-tier evaluation paper. All six are **already executed, verified, and backed by machine-readable artifacts** in `data_output/eval_framework/`.
- **Secondary / Ablation Experiments (E7 to E9):** Value-add empirical analyses that strengthen the discussion and error analysis. Already completed.
- **High-Cost / Optional Future Extensions (E10 to E12):** Dependent on multi-hour GPU jobs or independent human annotators. Explicitly demarcated under *Threats to Validity / Future Work*.

---

## 2. Detailed Specification for Core & Essential Experiments

### Experiment E1: Controlled Prerequisite Classification Benchmark
* **Research Question:** Can an unconstrained local 7B open-weight LLM discern directional prerequisite dependencies from textbook prose better than chance, deterministic rules, and zero-parameter structural priors?
* **Hypothesis:** Standalone local 7B LLMs operate near chance on directional prerequisite extraction due to symmetric definitional patterns in expository prose, whereas textbook reading order carries an overwhelming inductive signal.
* **Independent Variable:** Classification methodology (`Random`, `rule_v3`, `kgx_v2`, `kgx_v2_hybrid`, `Book Order`).
* **Controlled Variables:** Concept vocabulary ($N = 65$), candidate pair set ($N = 868$ common covered pairs), evaluation corpus (CK-12 Geometry), zero-shot conditions.
* **Dataset & Evaluation Set:** AL-CPL Basic Geometry ($260$ true positives, $608$ true negatives in common covered set).
* **Baselines:** Uniform Random Guessing, Zero-Parameter Book-Order Prior.
* **Metrics:** Edge Precision, Edge Recall, Edge $F_1$, Transitive Closure $F_1$, ROC-AUC, Directional Accuracy ($N_{\text{correct}} / N_{\text{pos}}$).
* **Statistical Test:** Clustered bootstrap over query concepts ($2,000$ resamples) for 95% CIs; Wilson score interval for directional accuracy.
* **Status:** **COMPLETE.** Logged in `prerequisite_report.json`.
* **Interpretation:** Standalone 7B LLM achieves ROC-AUC = $0.503$ [0.49, 0.51] and $50.0\%$ directional accuracy. Book order achieves ROC-AUC = $0.868$ [0.81, 0.91] and $96.5\%$ directional accuracy.

---

### Experiment E2: Pipeline Recall Bottleneck Decomposition
* **Research Question:** At what architectural stage does the automated pipeline discard the majority of ground-truth pedagogical dependencies?
* **Hypothesis:** Candidate-pair generation (sparse sentence co-occurrence) imposes a catastrophic upper-bound recall ceiling long before relation classification is performed.
* **Independent Variable:** Pipeline stage ($S_1$: Concept parsing $\to$ $S_2$: Lexicon matching $\to$ $S_3$: Candidate pair generation $\to$ $S_4$: Relation classification $\to$ $S_5$: Transitive closure reachability).
* **Controlled Variables:** Total AL-CPL ground-truth positives ($N = 524$).
* **Metrics:** Cumulative Positive Retention ($N_{\text{retained}}$), Stage Recall Ceiling ($R_{\text{ceiling}}$), Stage Loss Percentage ($\% \text{loss}$).
* **Status:** **COMPLETE.** Traced in `concepts_report.json` and `prerequisite_report.json`.
* **Interpretation:** Concept extraction drops max recall to $56.7\%$ ($227/524$ lost); candidate generation drops it further to $32.3\%$; classification drops direct edge recall to $1.5\%$; transitive closure partially recovers reachability to $39.9\%$ in the hybrid graph.

---

### Experiment E3: Structural Prior & Neuro-Symbolic Hybrid Ablation
* **Research Question:** Does the neuro-symbolic hybrid improve over the zero-parameter book-order baseline by leveraging neural relatedness, or is its performance an artifact of the reading-order forward gate?
* **Hypothesis:** The hybrid's high directional accuracy is inherited almost entirely from the book-order gate, with the LLM providing only marginal precision refinement over spurious co-occurrences.
* **Independent Variable:** Gating signal combinations (Book Order alone, Book Order $\times$ Co-occurrence, Book Order $\times$ LLM relatedness).
* **Controlled Variables:** Same $N=868$ candidate pairs, identical candidate concepts.
* **Metrics:** Closure $F_1$, ROC-AUC, NDCG@10.
* **Statistical Test:** Paired sign-flip permutation test ($p < 0.05$).
* **Status:** **COMPLETE.** Logged in `hybrid.py` evaluation and `weights_report.json`.
* **Interpretation:** Book order alone achieves ROC-AUC = $0.868$. Adding LLM relatedness reaches $0.888$ ($\Delta = +0.020$). The LLM contributes a modest precision filter, but does not provide directional intelligence.

---

### Experiment E4: Edge Weighting & Saaty AHP Ablation
* **Research Question:** Does combining semantic, co-occurrence, and document-proximity features via Saaty's Analytic Hierarchy Process (AHP) improve prerequisite ranking over simple co-occurrence?
* **Hypothesis:** Multi-criteria AHP weighting is functionally redundant; sentence co-occurrence ($C$) alone drives the entire ranking performance, while lexical definition overlap ($S$) provides zero discriminative utility.
* **Independent Variable:** Scoring formulation (AHP $0.52S + 0.24C + 0.09P + 0.15E$ vs. $C$-only vs. $S$-only vs. $P$-only vs. $E$-only vs. Book Order gap).
* **Controlled Variables:** AL-CPL query concepts ($N = 43$ queries with positive dependencies).
* **Metrics:** NDCG@5, NDCG@10, Mean Average Precision (MAP).
* **Statistical Test:** Paired bootstrap resampling across queries ($2,000$ iterations).
* **Status:** **COMPLETE.** Logged in `weights_report.json`.
* **Interpretation:** $C$-only (NDCG@10 = $0.723$) matches or slightly exceeds AHP ($0.709$, $p=0.68$). Definition overlap $S$-only (NDCG@10 = $0.589$) is statistically indistinguishable from random tie-breaks ($0.582$, $p=0.53$).

---

### Experiment E5: Multi-Relation Reference-Free Structural Diagnostics
* **Research Question:** How frequently do automated rule-based and LLM pipelines violate formal ontological constraints across non-prerequisite relations (*Part-of*, *Application*, *Extension*, *Similarity*)?
* **Hypothesis:** Automated extractors suffer from systematic category errors, specifically confounding meronymy (*Part-of*) with hyponymy (*Is-a*), and emitting contradictory reciprocal edges.
* **Independent Variable:** Pipeline type (`rule_v3` vs. `kgx_v2`).
* **Controlled Variables:** 5-relation schema ontology.
* **Metrics:** Contradiction Count ($N_{\text{contra}}$), Weak Evidence Count, Semantic Type Confusion Rate, Grounding Distance to Text (median tokens).
* **Status:** **COMPLETE.** Logged in `relation_checks_report.json`.
* **Interpretation:** `kgx_v2` emitted 43 semantic contradictions (e.g., pairs tagged as both *Part-of* and *Similarity*). Taxonomic confusion was audited in prompt and regex definitions where *"is a type of"* was erroneously assigned to *Part-of*.

---

### Experiment E6: Prerequisite Retrieval as a Structural Proxy for Gap Tracing
* **Research Question:** How effectively does traversing the extracted prerequisite graph retrieve upstream foundational dependencies for masked terminal concepts?
* **Hypothesis:** Traversal over sparse rule or LLM graphs fails to recover prerequisite paths, whereas structural order and hybrid graphs recover upstream ancestors with high fidelity.
* **Independent Variable:** Graph traversal backbone (`rule_v3`, `kgx_v2`, `kgx_v2_hybrid`, `Book Order`).
* **Controlled Variables:** Masked leaf concepts from AL-CPL ground-truth DAG.
* **Metrics:** Retrieval Precision@5 (P@5), Recall@10, Mean Reciprocal Rank (MRR).
* **Status:** **COMPLETE.** Logged in `gap_proxy_report.json`.
* **Interpretation:** P@5: `rule_v3` = $0.073$, `kgx_v2` = $0.047$, `kgx_v2_hybrid` = $0.461$, `Book Order` = $0.455$. Confirms that graph sparsity in standalone models destroys ancestor reachability.

---

## 3. High-Cost / Future Experiments (Demarcated in Paper)

* **Experiment E10 (External Baseline Integration - RefD & Cross-Encoder):**  
  * *Purpose:* Isolate sentence-level RefD (Liang et al., 2015) as an explicit column in Table 1 alongside Book Order.  
  * *Status:* **Feasible & Ready** (RefD already calculated in `hybrid.py`).
* **Experiment E11 (Multi-Model Parameter Scaling - 3B vs 7B vs 14B):**  
  * *Purpose:* Test whether 14B models overcome directional chance performance.  
  * *Status:* **Pending / Demarcated.** Compute-heavy.
* **Experiment E12 (Second-Domain Replication - OpenStax Physics):**  
  * *Purpose:* Test if reading order dominance generalizes to physics curricula.  
  * *Status:* **Frozen Protocol.** Documented in `second_domain_protocol.md`; designated as future work.
