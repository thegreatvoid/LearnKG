# Deliverable 3: Methodological Significance Analysis

**Audit Date:** 2026-10-24  
**Project:** LearnKG Comparative Evaluation  
**Framework:** `Methodological difference → Expected effect → Possible failure mode → Observable metric → Required experiment`

---

## 4.1 Hard-Coded Vocabulary vs. Automatic Concept Discovery

* **Methodological Difference:**  
  `rule_v3` restricts candidate extraction to a curated list of 130 canonical textbook concepts (`ck12_basic_geometry_concepts.txt`). `kgx_v2` uses an unsupervised spaCy noun-chunk extractor with document-frequency filtering and capitalization heuristics to discover 204 concepts directly from the text.
* **Expected Effect:**  
  The hard-coded list guarantees domain precision and filters conversational or expository noise. Automatic discovery enables domain-agnostic transfer and extracts emerging sub-concepts not present in static lexicons.
* **Possible Failure Mode:**  
  - *Hard-coded list:* Complete inability to discover unlisted technical terminology; zero transferability to a new curriculum without manual expert re-curation; drops critical abbreviations shorter than 3 characters (e.g., the *"HL"* Hypotenuse-Leg theorem).  
  - *Automatic discovery:* Over-extracts generic nouns (e.g., *"problem"*, *"example"*, *"figure"*); drops valid technical terms due to naive single-word filters (e.g., dropping *"area"*, *"similarity"*, and *"sine"* as weak single words).
* **Observable Metric:**  
  Concept Precision ($P_{\text{concept}}$), Concept Recall ($R_{\text{concept}}$) against AL-CPL 89-concept benchmark, and downstream candidate-pair coverage loss ($N_{\text{uncovered pos}}$).
* **Required Experiment:**  
  Evaluate both extractors against the blinded 200-item concept annotation sample in `data_output/eval_framework/annotation/concepts/` to compute true precision, recall, and $F_1$ over textbook vocabulary, decoupled from relation classification.

---

## 4.2 Rule-Based Relation Assignment vs. LLM Relation Classification

* **Methodological Difference:**  
  `rule_v3` relies on a deterministic regex parser matching Hearst patterns and pedagogical connectives (*"requires"*, *"is a prerequisite for"*, *"consists of"*). `kgx_v2` queries `qwen2.5:7b-instruct` with a multi-class prompt template using swap-sampling to score probabilities across 5 relation classes.
* **Expected Effect:**  
  LLM classification handles syntactic variance, complex subordinate clauses, and implicit semantic dependencies that lack exact lexical cue words.
* **Possible Failure Mode:**  
  - *Rule-based:* Extreme semantic fragility and catastrophic recall collapse ($R < 0.03$), as textbook authors rarely write explicit syntactic cue phrases like *"Concept A is a prerequisite for Concept B"*.  
  - *LLM-based:* Hallucinates semantic relationships between co-occurring entities; exhibits severe directional flip-flopping; suffers from prompt framing sensitivity; achieves near-chance accuracy ($50.0\%$) on directional arrows.
* **Observable Metric:**  
  Direct Edge Precision ($P_{\text{edge}}$), Edge Recall ($R_{\text{edge}}$), Edge $F_1$, and Directional Accuracy on positive benchmark pairs ($N_{\text{correct}} / N_{\text{decided}}$).
* **Required Experiment:**  
  A controlled relation classification experiment on the identical set of candidate pairs ($N=868$), isolating classifier decisions from candidate generation differences.

---

## 4.3 Sentence Co-occurrence vs. Broader Candidate Generation

* **Methodological Difference:**  
  `rule_v3` only evaluates concept pairs that appear within the same sentence or definition. `kgx_v2` generates candidate pairs across sentence co-occurrence, chunk co-occurrence (1,200 tokens), definition cross-references, and embedding nearest neighbors (generating 989 pairs).
* **Expected Effect:**  
  Broader candidate generation captures longitudinal curricular prerequisites spanning different sections and chapters.
* **Possible Failure Mode:**  
  Intra-sentence co-occurrence creates a severe recall ceiling: in AL-CPL Geometry, 43.3% of positive prerequisite pairs never co-occur within a single sentence across the entire textbook. Conversely, unrestricted candidate generation creates an $O(V^2)$ combinatorial explosion where true positive prevalence drops below $1\%$, flooding the classifier with false positives.
* **Observable Metric:**  
  Candidate Recall ($R_{\text{cand}} = \text{covered positives} / \text{total benchmark positives}$), Candidate Precision ($P_{\text{cand}}$), and Reachable Prerequisite Recall Upper Bound.
* **Required Experiment:**  
  Measure candidate recall against AL-CPL ground truth across varying window sizes: (1) Single sentence, (2) Single paragraph, (3) Section window, (4) Chapter window, and (5) Embedding top-$k$ nearest neighbors.

---

## 4.4 Semantic Reasoning vs. Textbook Reading Order

* **Methodological Difference:**  
  `kgx_v2` prompts an LLM to perform zero-shot semantic dependency reasoning on localized text snippets without providing page numbers. The structural baseline simply computes the character offset difference of first mentions: $p(A) < p(B) \implies A \to B$.
* **Expected Effect:**  
  Semantic reasoning should distinguish true conceptual dependency from mere incidental pedagogical sequencing (e.g., Chapter 2 being taught before Chapter 3 does not automatically make all Chapter 2 concepts prerequisites for all Chapter 3 concepts).
* **Possible Failure Mode:**  
  Local LLMs fail to discern the directional arrow when reading expository definitions because sentences define properties symmetrically. Conversely, reading order acts as a massive inductive cheat: high-school curricula are explicitly curated to be self-contained and progressive, meaning sequential order correlates strongly ($96.5\%$) with prerequisite dependency, masking the LLM's lack of true reasoning.
* **Observable Metric:**  
  Directional Accuracy on covered positives ($251/260$ for Book Order vs. $4/8$ for LLM), ROC-AUC, and NDCG@10 ranking.
* **Required Experiment:**  
  Evaluate reading order vs. LLM on "reverse-ordered" pedagogical structures (e.g., "Advanced Organizer" sections where a complex concept like *"Fractal"* or *"Polyhedron"* is previewed in Chapter 1 before foundational prerequisites are introduced in Chapter 4).

---

## 4.5 LLM-Only Extraction vs. Neuro-Symbolic Construction

* **Methodological Difference:**  
  `kgx_v2` relies solely on the LLM's prompt scores and greedy DAG pruning. `kgx_v2_hybrid` multiplies the LLM's undirected relatedness score by a directional reading-order forward gate and RefD co-citation rank: $\text{forward\_gate} \times \text{mean}(\text{rank}(\text{gap}), \text{rank}(\text{cooc}), \text{rank}(\text{RefD}), \text{rank}(\text{LLM\_rel}))$.
* **Expected Effect:**  
  The hybrid system should combine the semantic filtering of the LLM (eliminating spurious co-occurrences) with the robust directional prior of textbook chronology.
* **Possible Failure Mode:**  
  The apparent triumph of the hybrid ($F_1 = 0.786$, ROC-AUC = 0.888) is an illusion of the reading-order forward gate. If the LLM's marginal contribution over book order alone ($F_1 = 0.736$, ROC-AUC = 0.868) is negligible ($\Delta \text{AUC} = +0.020$), claiming a "neuro-symbolic breakthrough" is scientifically misleading.
* **Observable Metric:**  
  Marginal $\Delta F_1$, $\Delta \text{ROC-AUC}$, and ablation permutation tests comparing:
  1. Book order alone.
  2. Book order + Co-occurrence (Symbolic-only).
  3. Book order + LLM relatedness (Neuro-symbolic).
* **Required Experiment:**  
  A rigorous ablation isolating the exact performance of the hybrid when the LLM relatedness component is replaced with random noise vs. raw co-occurrence count.

---

## 4.6 Composite Edge Weighting vs. Simpler Scoring Functions

* **Methodological Difference:**  
  `rule_v3` computes edge weights using the Saaty Analytic Hierarchy Process ($W = 0.52S + 0.24C + 0.09P + 0.15E$, with $CR = 0.022$). The evaluation suite benchmarks this against individual factors: Co-occurrence alone ($C$), Definition lexical overlap alone ($S$), Chapter proximity alone ($P$), and Section Jaccard alone ($E$).
* **Expected Effect:**  
  Multi-criteria decision analysis should balance semantic affinity, distributional co-occurrence, and document structure into a calibrated edge confidence score.
* **Possible Failure Mode:**  
  Multi-factor formulas often create a facade of mathematical sophistication while deriving their entire predictive signal from a single dominant variable. In LearnKG, $S$ (weight 0.52) performs no better than random ranking, while $C$ (weight 0.24) carries the entire ranking utility. Furthermore, all 4 factors in the AHP formula are strictly symmetric ($W(A, B) = W(B, A)$), making the score fundamentally incapable of ranking directional prerequisites.
* **Observable Metric:**  
  NDCG@5, NDCG@10, and paired sign-flip permutation tests against AL-CPL queries.
* **Required Experiment:**  
  Cross-validated regression or coordinate ascent on factor weights to determine whether any multi-factor combination statistically outperforms simple co-occurrence count ($C$).

---

## 4.7 Schema Constraints and Graph Validation

* **Methodological Difference:**  
  Unconstrained pipelines emit arbitrary relational tuples. `kgx_v2_hybrid` enforces formal graph constraints: (1) DAG acyclicity on Prerequisite relations via greedy feedback arc set cycle elimination, and (2) Top-$k=3$ predecessor bounding.
* **Expected Effect:**  
  Guarantees graph validity for downstream algorithms (e.g., topological sort for learning path recommendation) and prevents early foundational nodes (e.g., *"Point"*, *"Line"*) from accumulating hundreds of incoming/outgoing edges.
* **Possible Failure Mode:**  
  Greedy cycle elimination can inadvertently remove valid prerequisite edges if a cycle contains both direct and indirect dependencies. Conversely, for non-prerequisite relations, the lack of ontological mutual-exclusion constraints permitted 43 severe semantic contradictions (e.g., asserting that Concept A is simultaneously a *Part-of* and a *Similarity* analog of Concept B).
* **Observable Metric:**  
  Cycle count in prerequisite graph, Transitive Closure $F_1$, and Contradiction Rate across multi-relation diagnostics in `relation_checks_report.json`.
* **Required Experiment:**  
  Compare graph validity, transitive reachability, and ground-truth edge retention before and after applying: (1) Greedy feedback arc set, (2) Transitive reduction, and (3) Ontological mutual-exclusion constraints (e.g., $\text{Part-of}(A, B) \implies \neg \text{Similarity}(A, B)$).
