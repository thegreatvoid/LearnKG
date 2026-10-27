# Research Protocol: Empirical Evaluation of Educational Knowledge Graph Construction

**Date:** 2026-10-23  
**Status:** Frozen Protocol for Conference Revision  
**Target Submission Track:** Empirical Evaluation / Resource Paper (ESWC, ISWC, EDM, AIED)

---

## 1. Research Questions & Hypotheses

- **RQ1 (Prerequisite Extraction Efficacy):** How accurately do locally deployed 7B LLM pipelines extract directed prerequisite dependencies from educational textbooks compared with deterministic rule-based and structural baselines?
  - *Hypothesis 1.1:* Unconstrained local LLMs struggle with directional prerequisite classification because textbook sentences frequently state properties without asserting explicit directional dependency cues.
  - *Hypothesis 1.2:* A simple reading-order heuristic ($p(A) < p(B)$) will exhibit high recall on textbook-grounded prerequisites due to the linear pedagogical prior of textbook instruction.

- **RQ2 (Pipeline Bottleneck Decomposition):** What proportion of prerequisite recall loss is attributable to concept extraction, concept normalization, candidate pair generation, and relation classification?
  - *Hypothesis 2.1:* Candidate pair generation (sparse sentence co-occurrence) imposes a severe upper bound on recall before the classification model is ever queried.

- **RQ3 (Efficacy of Structural Priors in Hybrid Systems):** Does a neuro-symbolic hybrid pipeline combine the strengths of LLM relatedness and structural sequence, or does its performance stem entirely from the reading-order heuristic?
  - *Hypothesis 3.1:* The hybrid system achieves higher precision than the raw reading-order baseline by using LLM/co-occurrence relatedness to prune false-positive early concepts.

- **RQ4 (Empirical Validity of Heuristic Relation Weighting):** How do Saaty AHP edge-weighting formulas compare to simpler statistical baselines (e.g., co-occurrence alone) for prerequisite ranking?
  - *Hypothesis 4.1:* Co-occurrence alone accounts for the ranking utility of multi-factor formulas, while lexical definition overlap contributes negligible discriminative power.

- **RQ5 (Multi-Relation Schema Adherence):** How reliably does the 5-relation educational ontology preserve relational semantics across Part-of, Application, Extension, and Similarity?
  - *Hypothesis 5.1:* LLM and pattern-based extractors suffer systematic taxonomic confusion, conflating hyponymy ("is a type of") with meronymy ("part-of").

---

## 2. Formal Dataset and Benchmark Definitions

### 2.1 Source Material
- **Corpus:** *CK-12 Basic Geometry* (`data_input/ck12_geometry/ck12_basic_geometry_concepts.txt`).
- **Characteristics:** High-school level curriculum; 130–204 extracted domain concepts; 12 chapters with explicit numbered sections.

### 2.2 External Ground Truth
- **Benchmark:** AL-CPL Geometry (Liang et al., 2015, AAAI 2018).
- **Size:** 1,681 concept pairs (524 positive prerequisite pairs, 1,157 negative pairs).
- **Semantics:** Directed pairs $(A, B)$ where $B$ is a prerequisite of $A$, evaluated as edge $B \to A$.
- **Transitive Property:** Benchmark positives are transitively closed; reachability in the generated KG DAG is evaluated via transitive closure.

### 2.3 Evaluation Sets
1. **Full Benchmark ($N = 1,681$):** Evaluates end-to-end extraction recall including missing concept loss.
2. **Matched Benchmark ($N = 1,025$):** Pairs where both concepts are successfully mapped to the textbook vocabulary.
3. **Common Covered Set ($N = 868$):** Exactly 260 positive pairs and 608 negative pairs whose concepts are mutually extracted and grounded across all compared KGs (`rule_2026-10-11`, `rule_v3`, `kgx_v2`, `kgx_v2_hybrid`). This provides the strictly controlled apples-to-apples comparison.

---

## 3. Evaluated Systems & Baselines

1. **Random Baseline:** Uniform random assignment / tie-break.
2. **Book-Order Baseline (Zero-Parameter):**
   $$\text{pred}(B \to A) = \begin{cases} 1 & \text{if } p(B) < p(A) \\ 0 & \text{otherwise} \end{cases}$$
   where $p(c)$ is the first character offset of concept $c$ in the text.
3. **`rule_v3`:** Hand-crafted regex and pedagogical connective parser with hard-coded domain lexicon.
4. **`kgx_v2` (Grounded Local LLM):** Zero-shot Ollama `qwen2.5:7b-instruct` prompt with order-swap debiasing and grounded text verification.
5. **`kgx_v2_hybrid` (Neuro-Symbolic):** Gated combination of reading order, co-occurrence, RefD, and LLM relatedness with top-$k$ pruning and DAG cycle removal.

---

## 4. Primary and Secondary Metrics

### 4.1 Classification Metrics
- Direct-Edge Precision ($P$), Recall ($R$), and $F_1$.
- Transitive Closure Precision, Recall, and $F_1$ (reachability on DAG).
- ROC-AUC with 95% DeLong / Bootstrap Confidence Intervals.

### 4.2 Ranking Metrics
- NDCG@5, NDCG@10 on query concepts (ranking foundational prerequisites for an advanced concept).
- Precision@5, Recall@10.

### 4.3 Structural & Reference-Free Metrics
- Directional Accuracy: proportion of positive benchmark pairs where predicted direction points forward in book order.
- Contradiction Rate: detected cycles, reciprocal directed edges, and cue mismatches.
- BIGS Grounding: semantic distance between extracted triples and nearest supporting text sentences.

---

## 5. Statistical Controls
- **Bootstrap Resampling:** 2,000 bootstrap iterations over query concepts to preserve cluster dependence within concepts.
- **Significance Testing:** Paired sign-flip permutation tests and two-sided binomial tests against random direction ($p = 0.5$).
- **Significance Level:** $\alpha = 0.05$. Confidence intervals reported at 95%.
- **Deterministic Evaluation:** Fixed random seed (`seed = 0`) across all bootstrap loops.
