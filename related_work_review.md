# Literature Review and Research Gap Analysis

**Date:** 2026-10-23  
**Target Submission:** Peer-reviewed Conference in Knowledge Engineering / Semantic Web / Educational AI (ESWC / ISWC / EDM / AIED)  
**Topic:** Educational Knowledge Graph Construction with Local LLMs and Structural Priors

---

## 1. Landscape of Related Research

### 1.1 Automated Concept Prerequisite Learning (CPL)
1. **Liang et al. (AAAI 2015, AAAI 2018):**
   - *Core Contribution:* Introduced the AL-CPL (Active Learning Concept Prerequisite Learning) benchmark and the Reference Distance (RefD) metric:
     $$\text{RefD}(A, B) = \frac{N(A \to B)}{N(A)} - \frac{N(B \to A)}{N(B)}$$
     where $N(A \to B)$ measures co-citation or cross-reference frequencies.
   - *Findings:* Verified on Wikipedia corpora that earlier, foundational concepts tend to be cited by advanced concepts without reciprocal citations.
   - *Relevance to This Paper:* AL-CPL Geometry serves as our external ground-truth benchmark (1,681 pairs, 524 positives). Our evaluation shows that RefD and textbook reading order capture a similar underlying pedagogical linearity.

2. **Alzetta et al. (LREC 2020, Frontiers in AI 2021):**
   - *Core Contribution:* Investigated prerequisite extraction from instructional texts (Italian and English textbooks), establishing that linguistic features and linear text order are the strongest predictors in expository prose.
   - *Relevance:* Confirms our finding that reading order acts as an extremely strong prior in structured textbooks.

3. **Chen, Zou, Xie, & Cheng (IEEE TLT 2018, CIKM 2019):**
   - *Core Contribution:* Proposed topological graph construction for learning dependencies, emphasizing directed acyclic graph (DAG) properties and transitivity.
   - *Relevance:* Informs our DAG-consistency enforcement (`consistency.py`) and transitive-closure reachability metrics.

4. **Roy et al. (EDM 2019):**
   - *Core Contribution:* Evaluated supervised and unsupervised prerequisite learning algorithms on MOOC lecture transcripts and textbooks.
   - *Findings:* Found that standard unsupervised NLP classifiers struggle with directional asymmetry unless explicit temporal or pedagogical sequence constraints are enforced.

---

### 1.2 LLMs for Knowledge Graph Construction
1. **Trajanoska et al. (IEEE Access 2023) & Carta et al. (ISWC 2023):**
   - *Core Contribution:* Evaluated large commercial LLMs (GPT-3.5, GPT-4) for open relation extraction and entity linking.
   - *Findings:* High few-shot precision on standard benchmarks (CoNLL04, TACRED), but substantial hallucination of ungrounded entities and relation drift.
   - *Gap Addressed by Our Work:* These studies evaluated massive closed-source APIs on general encyclopedic data. They did not assess resource-constrained, local open-weight models (7B/3B) on curriculum-constrained educational textbooks, where privacy, offline deployment, and strict domain boundaries are required.

2. **Kommineni et al. (Semantic Web Journal 2024):**
   - *Core Contribution:* Comprehensive benchmark of open-source LLMs (Llama-2, Mistral) on knowledge extraction, showing that smaller local models suffer severe schema-conformance drops and prompt sensitivity.
   - *Relevance:* Aligns with our diagnosis in `kgx_v2`, where the 7B LLM hallucinated entity types and failed to maintain directional consistency.

---

### 1.3 Neuro-Symbolic Knowledge Graphs & Structural Priors
1. **Hamilton et al. (Graph Representation Learning 2020) & Ji et al. (IEEE TNNLS 2021):**
   - Emphasized that purely neural relation extractors lack inductive structural biases (acyclicity, transitivity, anti-symmetry).
   - *Our Approach:* Our hybrid pipeline bridges this gap by marrying neural semantic relatedness with symbolic reading-order gating and greedy DAG cycle elimination.

---

## 2. Competitive Positioning Matrix

| Aspect | Classic CPL (Liang et al., Alzetta et al.) | Commercial LLM Extraction (Carta et al., Trajanoska et al.) | LearnKG (This Study) |
|---|---|---|---|
| **Primary Domain** | Wikipedia / MOOC transcripts | General encyclopedic corpora | Expository STEM Textbook (CK-12 Geometry) |
| **Model Type** | Traditional ML (SVM, RF) + hand-crafted RefD/NLP features | Closed-source cloud LLMs (GPT-4) | Locally deployable open-weight LLMs (Qwen-2.5 7B) |
| **Relation Scope** | Binary Prerequisite only ($A \to B$) | General open relations / Wikidata | Multi-relation educational ontology (Prerequisite, Part-of, Application, Extension, Similarity) |
| **Structural Bias** | Implicit sequence features | Ignored / Prompt-only | Formal ablation of reading-order gating + DAG constraints |
| **Evaluation Rigor** | Precision / Recall on cross-validation | Prompt accuracy on sampled subsets | Rigorous benchmark evaluation (AL-CPL) + Reference-free structural diagnostics + Blinded annotation package |

---

## 3. The Specific Scientific Gap and Defensible Contribution

### The Research Gap:
While commercial LLMs can extract general relational triplets, educational institutions and schools require **local, privacy-preserving, and computationally feasible** solutions. However, it was previously unknown:
1. Whether a sub-10B parameter model deployed on consumer hardware can reliably discern directional prerequisite dependencies from expository textbook prose.
2. How much predictive signal originates from the language model's parametric reasoning versus the textbook's sequential pedagogical structure (the reading-order prior).
3. Where the pipeline actually breaks down: at concept extraction, candidate pairing, directional classification, or graph construction.

### The Defensible Contribution:
Rather than claiming that a local 7B LLM achieves state-of-the-art educational KG construction, this study provides a **controlled, empirical critique and diagnostic evaluation**:
- Demonstrates that unconstrained local LLMs operate near chance on directional prerequisite extraction ($\text{ROC-AUC} \approx 0.503$).
- Demonstrates that a zero-parameter reading-order baseline substantially outperforms the 7B model ($\text{ROC-AUC} = 0.868, F_1 = 0.736$).
- Demonstrates that neuro-symbolic coupling (combining LLM semantic relatedness with structural reading-order gating) achieves the strongest overall performance ($F_1 = 0.786$).
- Deconstructs the pipeline bottlenecks quantitatively, proving that candidate generation and directional ambiguity account for the vast majority of recall loss.
- Evaluates multi-relation schema adherence across 5 educational relations, uncovering severe taxonomic vs. meronymic conflation.
