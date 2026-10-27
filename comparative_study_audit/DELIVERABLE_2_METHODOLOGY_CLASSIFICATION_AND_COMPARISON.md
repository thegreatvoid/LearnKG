# Deliverable 2: Methodology Classification & Detailed Comparison

**Audit Date:** 2026-10-24  
**Project:** LearnKG Comparative Evaluation  
**Auditor:** Senior AI Researcher & Knowledge Graph Evaluation Specialist

---

## 1. Classification Architecture: Pipelines vs. Baselines vs. Scoring Functions

To satisfy scientific rigor, the evaluated approaches are partitioned into two distinct categories:

### Table 2.1: End-to-End Construction Methodologies
These three systems extract concepts, propose relationships, assign ontology types, and assemble a persistent knowledge graph from raw text.

| Dimension | 1. Rule-Based Pipeline (`rule_v3`) | 2. Standalone Local LLM (`kgx_v2`) | 3. Neuro-Symbolic Hybrid (`kgx_v2_hybrid`) |
|---|---|---|---|
| **A. Methodological Foundation** | **Symbolic / Heuristic NLP:** Assumes that pedagogical and conceptual relations are overtly signaled by textbook formatting, section hierarchy, definitional syntactic patterns (Hearst patterns), and connective cue words. | **Generative / Neural Prompting:** Assumes that an instruction-tuned open-weight language model (`qwen2.5:7b-instruct`) can discern multi-class semantic relations between concepts from local text context when queried with swap-sampled JSON prompts. | **Post-Processing Neuro-Symbolic Synthesis:** Combines unconstrained neural relatedness scores from `kgx_v2` with deterministic structural constraints (reading order forward gate, RefD co-occurrence, top-$k$ degree bounding, and DAG cycle pruning). |
| **B. Input Representation** | Parsed blocks, sentence-level tokens, hard-coded domain lexicon, section/chapter markers, verbatim definition clauses. | Unsupervised noun-phrase candidates, chunk context strings, pair prompt templates with role-swapped examples. | Precomputed `kgx_v2` pair scores, first-mention character offsets in source textbook, sentence co-occurrence sets. |
| **C. Concept Extraction & Normalization** | **Vocabulary-Grounded:** Filters candidates against a hard-coded textbook lexicon (130 concepts). Uses alias dictionaries, fuzzy stem matching, and subject-verb extraction for first definitions. | **Unsupervised Grounded Discovery:** Extracts noun chunks via spaCy, filters by frequency and document position, binds to verbatim first-mention sentences (204 concepts). | Inherits the exact 204 concept nodes extracted and normalized by `kgx_v2`. |
| **D. Candidate-Pair Generation** | **Intra-Sentence & Definition Cue Matching:** Exhaustively checks sentences containing two matched concepts, or concept-definition co-occurrences. Concepts from distant chapters cannot form candidates unless explicitly co-mentioned. | **Hybrid Candidate Generator:** Multi-source proposal combining sentence co-occurrence, chunk co-occurrence, definition cross-references, and embedding nearest neighbors (989 candidate pairs). | Evaluates the full Cartesian candidate set of all extracted concepts ($204 \times 203 = 41,412$ pairs), filtered by forward reading order and top-$k$ relatedness. |
| **E. Relationship Extraction** | **Pattern & Cue Rules:** Evaluates regex triggers (`KEYWORD_RES`, `ONTOLOGY_PATTERNS`). Prerequisite direction is decided by passive voice inversion or book order fallback. | **Swap-Sampled Multi-Class Prompt:** Queries local LLM with $(u, v)$ and $(v, u)$; averages probabilities across 5 relation classes. Enforces JSON schema. | Multi-signal rank product: $\text{forward\_gate} \times \text{mean}(\text{rank}(\text{gap}), \text{rank}(\text{cooc}), \text{rank}(\text{RefD}), \text{rank}(\text{LLM\_rel}))$. |
| **F. Graph Construction & Constraints** | Assembles directed graph. Weights computed via Saaty AHP ($W = 0.52S + 0.24C + 0.09P + 0.15E$). Cycles permitted unless post-pruned. | Assembles multi-relation graph (545 edges). Greedy feedback arc set algorithm removes cycles on Prerequisite edges to enforce a DAG. | Enforces strict DAG on Prerequisite edges; assigns non-prerequisite relations from LLM to remaining unlinked pairs. Top-$k=3$ predecessor limit. |
| **G. Computational Profile** | **Low:** Deterministic execution (~5–10 seconds runtime, zero GPU requirements, zero LLM token cost). | **High:** Local neural inference (~45–90 minutes runtime on 7B Ollama, ~2,000–3,000 prompt calls, 8GB+ VRAM required). | **Low to Moderate:** ~15–30 seconds matrix computation given precomputed LLM run scores. |

---

### Table 2.2: Structural Baselines and Scoring Ablations
These systems do not generate complete multi-relational knowledge graphs; they provide comparative baselines or ranking ablations for prerequisite edges.

| Dimension | 4. Zero-Parameter Reading-Order Baseline | 5. Saaty AHP Composite Weighting | 5b. Sentence Co-occurrence ($C$) Alone | 5c. Lexical Definition Overlap ($S$) Alone |
|---|---|---|---|---|
| **A. Foundation** | **Temporal Presentation Prior:** Assumes instructional textbooks are structured linearly such that foundational concepts are introduced before dependent concepts ($p(A) < p(B) \implies A \to B$). | **Multi-Criteria Decision Analysis:** Combines 4 subjective factors (Definition overlap $S$, Co-occurrence $C$, Chapter proximity $P$, Section Jaccard $E$) using pairwise Saaty comparison matrices ($CR = 0.022$). | **Distributional Association:** Assumes that concepts sharing pedagogical dependency are repeatedly co-mentioned within the same sentence context ($C = \min(1.0, n_{\text{sentences}}/3)$). | **Definitional Similarity:** Assumes that dependent concepts share core terminology in their textbook definitions ($S = \text{Jaccard}(\text{def}_A, \text{def}_B)$). |
| **B. Inputs Used** | Character offset of first concept mention in raw text $p(c)$. | Grounded definition clauses, sentence co-occurrences, chapter indices, section IDs. | Sentence token sets across corpus. | Cleaned definition strings from textbook parser. |
| **C. Directional Capability** | Strictly directed ($p(A) < p(B) \implies$ score $> 0$; $p(A) \ge p(B) \implies$ score $\le 0$). | Strictly symmetric: $W(A, B) = W(B, A)$. Cannot determine edge directionality. | Strictly symmetric: $C(A, B) = C(B, A)$. Cannot determine edge directionality. | Strictly symmetric: $S(A, B) = S(B, A)$. Cannot determine edge directionality. |
| **D. Research Role** | Inductive baseline to quantify how much prerequisite signal is trivial textbook chronology. | Evaluated scoring model to test whether multi-factor weighting improves ranking over raw co-occurrence. | Feature ablation to isolate the primary predictive driver of edge weights. | Feature ablation to test the utility of lexical definitional grounding. |
| **E. Key Empirical Result** | $F_1 = 0.736$, ROC-AUC = 0.868, Directional Accuracy = 96.5% on AL-CPL. | NDCG@10 = 0.709 on AL-CPL prerequisite queries. | NDCG@10 = 0.723 ($p = 0.68$ vs. AHP; no loss of ranking efficacy). | NDCG@10 = 0.589 ($p < 0.001$ vs. Co-occurrence; statistically indistinguishable from random 0.577). |

---

## 3. Deep-Dive Across Dimensions A through G

### A. Methodological Foundations & Underlying Assumptions
- **The Heuristic Assumption (`rule_v3`):** Explicit connectives (e.g., *"requires"*, *"based on"*, *"is a type of"*) are assumed to have high precision. The fatal flaw is extreme sparsity: high-school textbooks explain concepts through examples and narrative theorems rather than explicit relational cue phrases, causing recall to collapse to $< 3\%$.
- **The Generative Assumption (`kgx_v2`):** 7B instruction-tuned LLMs are assumed to understand the conceptual hierarchy of domain knowledge. The empirical audit proves this assumption is false for standalone 7B models on expository text: without structural position hints, `qwen2.5:7b-instruct` operates at chance for directionality ($50.0\%$).
- **The Hybrid Assumption (`kgx_v2_hybrid`):** Assumes that the LLM provides semantic relatedness (pruning unrelated concept pairs) while the textbook reading order provides the directional arrow. This assumption is supported empirically, but raises questions about circularity.

### B. Input Representation & Textual Anchors
- `rule_v3` is tightly coupled to the pedagogical layout of CK-12 Geometry (parsed into 72 structure blocks: Chapter, Section, Definition, Theorem, Explanation).
- `kgx_v2` treats the text as unstructured chunks of 1,200 tokens, losing the explicit section boundaries but gaining flexibility.
- Both pipelines enforce an **evidence-grounding contract**: relation proposals require verbatim supporting sentences, preventing free hallucinations.

### C. Concept Extraction & Vocabulary Bias
- `rule_v3` achieves high concept precision because it searches for 130 pre-defined geometry terms. However, it cannot discover new concepts and drops abbreviations $< 3$ letters (missing *"HL"* theorem).
- `kgx_v2` extracts 204 concepts via noun-phrase chunking and frequency gating. However, it dropped multi-word acronyms (e.g., *"SSS"*, *"SAS"*) due to casing/frequency rules, and dropped foundational single words (e.g., *"area"*, *"similarity"*) due to a `weak_single_word` filter.
- **Both methods matched exactly 65 of 89 AL-CPL benchmark concepts (73.0% coverage).** Of the 24 missing benchmark concepts, 13 are completely absent from the CK-12 textbook body, representing an external benchmark misalignment rather than an extraction error.

### D. Candidate-Pair Generation: The Hidden Bottleneck
- Candidate generation is the single largest point of recall failure in both systems:
  - `rule_v3` only tests intra-sentence co-occurrences (misses all cross-sentence and cross-chapter prerequisites).
  - `kgx_v2` proposes 989 pairs out of 20,706 possible pairs ($4.7\%$).
- When mapped against the AL-CPL gold set, **43.3% of positive prerequisite pairs are discarded before the LLM or rule engine is ever invoked**.

### E. Relation Classification & Directional Reasoning
- For `kgx_v2`, direction classification is virtually coin-flip guessing (4 correct, 4 incorrect on covered AL-CPL positives). The LLM cannot reliably tell whether *A requires B* or *B requires A* when prompted on sentence excerpts.
- In contrast, textbook reading order ($p(A) < p(B)$) is directional for 251 out of 260 AL-CPL positives (**96.5% directional accuracy**).

### F. Graph Constraints & Consistency
- `kgx_v2_hybrid` applies a greedy feedback arc set algorithm to ensure that the Prerequisite subgraph is a Directed Acyclic Graph (DAG). This is theoretically necessary for curriculum sequencing (a concept cannot be its own prerequisite through transitive cycles).
- However, for non-prerequisite relations (*Part-of*, *Application*, *Extension*, *Similarity*), no formal ontology consistency check was enforced in the baseline runs, leading to 43 identified semantic contradictions (e.g., pairs asserted as both *Part-of* and *Similarity*).

### G. Computational Profiles
- `rule_v3`: Run time ~8.4s, Memory ~180MB RAM, CPU only.
- `kgx_v2`: Run time ~68m, Memory ~9.2GB VRAM (Ollama `qwen2.5:7b-instruct`), ~2,400 forward passes.
- `kgx_v2_hybrid`: Run time ~22s post-processing over `kgx_v2` cache.
