# Research Artifact Inventory: LearnKG Comparative Study

This document provides a comprehensive inventory of all source code, datasets, evaluation results, figures, tables, benchmarks, annotations, literature, manuscripts, and reproducibility artifacts present in the repository, serving as the empirical foundation for the comparative evaluation paper in `paper_submission/`.

---

## 1. Primary Artifact Inventory Table

| Category | Component / Artifact | Exact Repository Location | Format / Details | Status & Notes |
|:---|:---|:---|:---|:---|
| **Method Implementation** | Pipeline 1: Symbolic (`rule_v3`) | `src/rule_v3/` | Python modules (`extract_concepts.py`, `build_graph.py`) | Handcrafted 130-term glossary, regex, co-occurrence scoring. |
| **Method Implementation** | Pipeline 2: Neural (`kgx_v2`) | `src/kgx_v2/` | Python modules (`extract_concepts.py`, `classify_relations.py`) | Ollama Qwen-2.5-7B, JSON structured prompt, local LLM inference. |
| **Method Implementation** | Pipeline 3: Hybrid (`kgx_v2_hybrid`) | `src/kgx_v2_hybrid/` | Python modules (`build_hybrid.py`) | Combines LLM relatedness + structural reading-order forward gating. |
| **Method Implementation** | Baseline 4: Reading Order | `eval/book_order_baseline.py` | Python script | Zero-parameter structural baseline ($pos(u) < pos(v)$). |
| **Method Implementation** | Baseline 5: Uniform Random | `eval/evaluate_prereq_benchmarks.py` | Python script | Uniform edge assignment ($P=0.50$, $AUC=0.50$). |
| **Method Implementation** | Ablation: Saaty AHP | `src/rule_v3/ahp_weights.py` | Python script ($W=0.52S+0.24C+0.09P+0.15E$) | Pairwise comparison matrix ($CR=0.022$). |
| **Dataset (Corpus)** | CK-12 Basic Geometry | `data_input/textbook/` | Markdown / TXT (43 sections, 6,104 sentences, 126k tokens) | Open-licensed CC BY-NC 3.0 educational textbook. |
| **Benchmark** | AL-CPL Geometry | `data_input/benchmarks/al_cpl/` | CSV / TSV ground truth | 89 concepts, 98 directed prerequisite edges. |
| **Concept Mapping** | Benchmark Matcher | `eval/match_concepts.py` | CSV / JSON | Levenshtein $\ge 0.85$ + synonym glossary; 65/89 concepts mapped ($73\%$). |
| **Evaluation Framework** | Benchmark Evaluator | `eval/evaluate_prereq_benchmarks.py` | Python script | Computes Edge F1, Transitive Closure F1, ROC-AUC on covered pairs ($N=868$). |
| **Evaluation Results** | Benchmark Metrics Manifest | `data_output/eval_framework/prereq_evaluation_summary.json` | JSON summary | Edge F1, Closure F1, ROC-AUC, 95% bootstrap CIs ($B=1000$). |
| **Evaluation Results** | Ranking & Weighting Ablation | `data_output/eval_framework/weighting_ablation_results.json` | JSON / CSV summary | NDCG@5, NDCG@10, MAP, paired permutation test $p$-values. |
| **Evaluation Results** | Multi-Relation Consistency | `data_output/eval_framework/relation_diagnostics.json` | JSON audit log | 43 semantic contradictions, reciprocal checks, schema consistency. |
| **Evaluation Results** | Textual Grounding (BIGS) | `data_output/eval_framework/bigs_grounding_eval.json` | JSON summary | Sentence citation density and verbatim definition grounding. |
| **Evaluation Results** | Prerequisite Retrieval | `data_output/eval_framework/prereq_retrieval_eval.json` | JSON summary | Graph reachability, ancestor traversal, Precision@5 ($K=5$). |
| **Figures** | Architecture Flowchart | `paper_submission/figures/methodology_flowchart.tex` | LaTeX / TikZ vector source | Complete pipeline and evaluation flow diagram. |
| **Figures** | Information Taxonomy | `paper_submission/figures/methodology_comparison.tex` | LaTeX / TikZ vector source | Visual comparison of rules, LLM, reading order, and AHP signals. |
| **Tables** | Methodology Comparison | `paper_submission/tables/methodology_comparison.tex` | LaTeX `table*` environment | 16-dimension comparative matrix. |
| **Tables** | Main Benchmark Results | `paper_submission/tables/main_results.tex` | LaTeX `table*` environment | Controlled benchmark results on $N=868$ common pairs with 95% CIs. |
| **Tables** | Weighting Ablation | `paper_submission/tables/weighting_ablation.tex` | LaTeX `table` environment | Ranking quality comparison across 7 scoring configurations. |
| **Literature** | Verified References | `paper_submission/references.bib` | BibTeX format (10 verified citations) | Liang (2015, 2018), Alzetta (2020, 2021), Chen (2018), Roy (2019), Carta (2023), Trajanoska (2023), Kommineni (2024), Ji (2021), Saaty (1980), Hearst (1992). |
| **Manuscripts** | Working Draft | `paper_submission/main.tex` | Modular LaTeX document | Double-blind conference-format complete paper. |
| **Manuscripts** | Legacy Draft | `paper_conference_revision.tex` | LaTeX document | Preserved historical draft (untouched). |
| **Reproducibility** | Verification Commands | `paper_submission/reproducibility.tex` | Documented commands | Exact evaluation scripts and command-line arguments. |

---

## 2. Status of Missing or Unperformed Evidence

In compliance with the strict constraint **"DO NOT RUN NEW EXPERIMENTS"**, the following claims are explicitly marked as unsupported or limited in the manuscript:

1. **Multi-Domain Generalization:** No second-domain textbook (e.g., Biology, Physics, or Computer Science) has been processed. All quantitative findings apply strictly to the CK-12 Basic Geometry corpus.
2. **Multi-Model Scaling:** Only Ollama `Qwen-2.5-7B` was evaluated. Performance of larger open-weight models (e.g., 70B) or proprietary frontier APIs (e.g., GPT-4o, Claude 3.5 Sonnet) is unmeasured.
3. **Multi-Relation Human Ground Truth:** The AL-CPL benchmark provides ground truth exclusively for directed prerequisite relations. Non-prerequisite relations (*Part-of*, *Application*, *Extension*, *Similarity*) are evaluated via internal structural consistency checks and cannot claim verified human precision/recall.
4. **Learner-Specific Pedagogical Utility:** Downstream prerequisite retrieval was evaluated using structural graph reachability rather than an active human learning trial.
