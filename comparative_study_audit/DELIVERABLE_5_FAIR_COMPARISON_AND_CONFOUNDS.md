# Deliverable 5: Fair-Comparison Audit & Confound Analysis

**Audit Date:** 2026-10-24  
**Project:** LearnKG Comparative Evaluation  
**Auditor:** Senior AI Researcher & Knowledge Graph Evaluation Specialist

---

## 1. Confound Analysis: Fifteen Potential Confounds

When comparing `rule_v3`, `kgx_v2`, `kgx_v2_hybrid`, and the `Book-Order` baseline, raw end-to-end metrics conflate multiple variables. Below is the systematic audit of the fifteen potential confounds:

| # | Confound Variable | Present in LearnKG? | Impact & Likely Direction of Influence | Required Control / Evaluation Protocol |
|---|---|---|---|---|
| **1** | **Different Concept Vocabularies** | **Yes** (`rule_v3`: 130 nodes; `kgx_v2`: 204 nodes). | `kgx_v2` has 57% more nodes. If evaluated end-to-end, unmatched nodes dilute edge density and distort macro-recall. | Restrict comparative evaluation to the **Common Covered Concept Set** ($N = 65$ concepts mutually matched to AL-CPL). |
| **2** | **Different Candidate-Pair Sets** | **Yes** (`rule_v3`: intra-sentence only; `kgx_v2`: 989 pairs; `hybrid`: 41,412 pairs; `Book Order`: all pairs). | Gives `hybrid` and `Book Order` access to cross-chapter pairs that `rule_v3` was never allowed to see, creating an artificial candidate-generation advantage. | Evaluate models under **Setting A (Controlled Pairs: $N=868$)** where all methods classify the exact same pairs, separate from **Setting B (End-to-End)**. |
| **3** | **Different Numbers of Nodes** | **Yes** (130 vs. 204). | Higher node count increases transitive path lengths in closure calculations ($G^+$). | Subgraph projection: compute transitive closure reachability only on the induced subgraph of common concepts. |
| **4** | **Different Numbers of Edges** | **Yes** (Prerequisite edges: `rule_v3` = 27; `kgx_v2` = 54; `hybrid` = 518; `Book Order` = 260+). | Dense graphs trivially achieve higher recall and closure reachability at the expense of precision. | Report **Top-$k$ Ranking Metrics (NDCG@5, NDCG@10, P@5)** and Precision-Recall Curves across thresholds, rather than single arbitrary operational cutoffs. |
| **5** | **Different Relation Types** | **Yes** (5 relation types extracted, but AL-CPL only evaluates *Prerequisite*). | Evaluators might mistakenly assume all 5 types are validated by the benchmark. | Explicitly report that AL-CPL evaluates **Prerequisite only**. The other four types are evaluated via reference-free structural diagnostics and blinded human sampling. |
| **6** | **Different Edge-Weight Scales** | **Yes** (`rule_v3`: AHP $[0, 1]$; `kgx_v2`: uncalibrated prompt score $[0, 1]$; `hybrid`: rank product $[0, 1]$; `Book Order`: character gap). | Precludes using a single universal classification threshold (e.g., $w \ge 0.5$). | Use **Threshold-Independent Metrics (ROC-AUC, Average Precision)** and **Percentile Rank Standardization**. |
| **7** | **Different Benchmark Coverage** | **Controlled** in `kg_eval.framework`. | Historically, comparing models on different covered subsets produced invalid comparisons. | Enforce the **Common Covered Set ($N=868$ pairs)** where every concept pair is present in all models. |
| **8** | **Treatment of Unmatched Concepts** | **Controlled** in `kg_eval.framework`. | Treating unmatched benchmark concepts as false negatives penalizes an extractor for terms completely missing from the textbook body. | Benchmark pairs with concepts absent from the textbook (13 concepts) are formally categorized as **External Benchmark Misalignment (Coverage Loss)**, not model classification errors. |
| **9** | **Access to Structural Information** | **Yes** (`rule_v3`: section/chapter markers; `Book Order`: character offset; `kgx_v2`: chunk text only; `hybrid`: explicit book order gate). | `hybrid` and `Book Order` have explicit access to linear page order; `kgx_v2` was deliberately blinded to document position. | Explicitly annotate `uses_book_order: true/false`. Do NOT claim the hybrid's directional accuracy is an emergent neural capability. |
| **10** | **Use of External Information** | **No** (All models restricted to CK-12 Geometry text). | None of the methods query Wikipedia, ConceptNet, or external web corpora. | Maintains the **Strict In-Text Provenance Contract**. |
| **11** | **Threshold Selection Procedures** | **Controlled**. | Tuning a decision threshold on the test set inflates reported $F_1$. | All direct edge metrics use the pipeline's native binary outputs; ranking metrics evaluate continuous scores without thresholding. |
| **12** | **Post-Processing Constraints** | **Yes** (`kgx_v2_hybrid` enforces DAG acyclicity and top-3 degree bounds; `rule_v3` does not). | DAG cycle removal directly boosts transitive closure precision. | Measure ablation of cycle removal: evaluate `kgx_v2_hybrid` with and without DAG enforcement. |
| **13** | **Computational Budgets** | **Yes** (`rule_v3`: CPU 8s; `kgx_v2`: 7B GPU 68m). | If a 68-minute GPU run performs worse than an 8-second rule run, this is a central scientific finding, provided candidate inputs were fair. | Report runtime, parameter scale, token consumption, and compute profile alongside accuracy metrics. |
| **14** | **Prompting Strategies** | **Controlled** within `kg_extract`. | Uncalibrated one-way prompts suffer from position and label bias. | `kgx_v2` uses order-swap debiasing (averaging $u \to v$ and $v \to u$). |
| **15** | **Training / Tuning Information** | **None** (All methods are zero-shot / unsupervised). | Precludes data leakage from AL-CPL into model weights. | No fine-tuning on AL-CPL was performed; AL-CPL serves strictly as a held-out test benchmark. |

---

## 2. The Two-Setting Evaluation Architecture

To ensure scientific honesty and prevent conflating candidate-generation bottlenecks with classifier ability, the paper must report results across two distinct settings:

### Setting A: Controlled Component Evaluation (Fixed Input)
* **Goal:** Measure pure relation classification and directional reasoning capability.
* **Protocol:** All systems are provided with the **identical candidate concept pairs ($N = 868$ common covered pairs)**.
* **Controlled Variables:** Concept vocabulary is frozen ($N = 65$ matched concepts); candidate set is frozen ($260$ true positives, $608$ true negatives).
* **Observed Difference:** Pure classifier performance (Edge Precision, Edge Recall, Edge $F_1$, Directional Accuracy, ROC-AUC).
* **Outcome:** Reveals that standalone 7B LLM classification operates at chance ($ROC-AUC = 0.503$, Acc = $50.0\%$), while reading order achieves $ROC-AUC = 0.868$ and Acc = $96.5\%$.

### Setting B: End-to-End Pipeline Evaluation (Raw Text to Graph)
* **Goal:** Measure real-world practical utility where a system must parse raw textbook text, discover concepts, generate candidate pairs, classify relations, and assemble a graph.
* **Protocol:** Each complete pipeline (`rule_v3`, `kgx_v2`, `kgx_v2_hybrid`) runs independently on raw text (`ck12_basic_geometry_concepts.txt`).
* **Observed Difference:** End-to-end recall over the entire 1,681-pair benchmark, accounting for:
  1. Concept extraction recall loss (drops max reachable recall to $0.567$).
  2. Candidate-pair generation recall loss (drops max reachable recall to $0.323$).
  3. Classification recall loss.
* **Outcome:** Quantifies the true end-to-end transitive closure reachability ($0.013$ for `rule_v3`, $0.010$ for `kgx_v2`, $0.399$ for `kgx_v2_hybrid`).
