# Empirical Claim Traceability Matrix: LearnKG Comparative Study

This document maps every substantive empirical claim, numerical result, and methodological assertion in `paper_submission/main.tex` directly to its underlying repository artifact, evaluation protocol, and verification status.

---

## 1. Primary Empirical Claims Matrix

| Claim in Paper | Existing Evidence Source | Reported Metric | Evaluation Conditions | Verification Status |
|:---|:---|:---|:---|:---|
| **Claim 1: Standalone Local LLM operates at chance** | `data_output/eval_framework/prereq_evaluation_summary.json`, `paper_conference_revision.tex` (Table 3) | $\text{ROC-AUC} = 0.503$ [95% CI: $0.49, 0.51$], $\text{Edge } F_1 = 0.030$, $\text{Dir Acc} = 4/8$ ($50.0\%$) | AL-CPL common covered pairs ($N=868$, 260 positive, 608 negative). Evaluated using zero-shot prompting on Qwen-2.5-7B. | **Directly Supported & Verified** (Artifact confirmed; CI encompasses $0.500$). |
| **Claim 2: Zero-parameter reading order dominates directional accuracy** | `data_output/eval_framework/prereq_evaluation_summary.json`, `eval/book_order_baseline.py` | $\text{ROC-AUC} = 0.868$ [95% CI: $0.81, 0.91$], $\text{Edge } F_1 = 0.736$, $\text{Dir Acc} = 251/260$ ($96.5\%$) | AL-CPL common covered pairs ($N=868$). Strict linear first-mention rule: $pos(u) < pos(v)$. | **Directly Supported & Verified** (Stored baseline output confirmed). |
| **Claim 3: Hybrid gains derive from reading-order prior** | `data_output/eval_framework/prereq_evaluation_summary.json`, `src/kgx_v2_hybrid/build_hybrid.py` | $\text{Closure } F_1 = 0.786$, $\text{ROC-AUC} = 0.888$, $\text{Dir Acc} = 71/72$ ($98.6\%$). LLM marginal AUC gain = $+0.020$. | Hybrid enforces $pos(u) < pos(v)$ forward gating constraint. Without gating, performance drops to LLM level. | **Directly Supported & Verified** (Code inspection confirms architectural prior). |
| **Claim 4: Rule-based extraction suffers from catastrophic recall** | `data_output/eval_framework/prereq_evaluation_summary.json`, `src/rule_v3/` | $\text{Precision} = 0.875$, $\text{Recall} = 0.027$, $\text{Candidate Recall} = 0.031$, $\text{Dir Acc} = 7/7$ ($100\%$) | AL-CPL common covered pairs ($N=868$). Limited by regex pattern matching and hand-crafted 130-term vocabulary. | **Directly Supported & Verified** (Evaluation summary confirmed). |
| **Claim 5: Benchmark concept coverage is bounded at 73%** | `eval/match_concepts.py`, `data_output/eval_framework/concept_mapping.json` | 65 out of 89 AL-CPL concepts mapped ($73.0\%$). $\text{rule\_v3}=130$, $\text{kgx\_v2}=204$. | Levenshtein edit distance $\ge 0.85$ + manual synonym glossary. 24 benchmark concepts missing from CK-12. | **Directly Supported & Verified** (Mapping table verified). |
| **Claim 6: Saaty AHP weighting is redundant to co-occurrence** | `data_output/eval_framework/weighting_ablation_results.json`, `paper_conference_revision.tex` (Table 4) | $\text{AHP NDCG@10} = 0.709$; $\text{Co-occ NDCG@10} = 0.723$ ($p=0.68$, ns); $\text{Raw Count} = 0.742$. | Query ranking over AL-CPL target concepts. Permutation test with $B=10,000$ resamples. | **Directly Supported & Verified** (Ablation JSON verified). |
| **Claim 7: Lexical definition overlap is uninformative** | `data_output/eval_framework/weighting_ablation_results.json` | $\text{Definition Overlap } S \text{ NDCG@10} = 0.589$ vs Random $0.582$ ($p < 0.001$ drop from Cooc). | AHP assigned 52% weight to $S$, but its ranking power is indistinguishable from random noise. | **Directly Supported & Verified** (Ablation JSON verified). |
| **Claim 8: Structural contradictions occur in unconstrained LLM graphs** | `data_output/eval_framework/relation_diagnostics.json` | 43 semantic contradictions detected (reciprocal *Part-of* / *Prerequisite*). | Automated consistency checker evaluating ontological acyclicity and asymmetry constraints. | **Directly Supported & Verified** (Diagnostic audit log verified). |

---

## 2. Classification of Scientific Assertions

To preserve scientific rigor, all assertions in the manuscript are explicitly classified into one of four epistemic tiers:

### Tier 1: Directly Supported Empirical Findings
- Standalone local LLM (Qwen-2.5-7B) fails to predict prerequisite directionality ($\text{Dir Acc} = 50.0\%$, chance level).
- Linear textbook order achieves $96.5\%$ directional accuracy and an edge $F_1$ of $0.736$.
- Co-occurrence alone matches or outperforms the 4-factor Saaty AHP formula ($p=0.68$, not significant).
- Lexical definition overlap performs at near-random levels ($\text{NDCG@10} = 0.589$).

### Tier 2: Qualified Architectural Findings
- The hybrid pipeline's performance ($\text{ROC-AUC} = 0.888$) is a compound result of structural gating and LLM pruning.
- The LLM's contribution in the hybrid is strictly precision-oriented (pruning false positives from $0.595$ to $0.845$) rather than dependency discovery.

### Tier 3: Methodological Interpretations
- The failure of local LLMs on definition snippets is attributed to expository symmetry: introductory textbook text describes concept interactions without explicit causal or pedagogical dependency markers.
- Candidate pair generation constitutes an unaddressed architectural bottleneck in educational KG pipelines, choking recall before relation classifiers are even executed.

### Tier 4: Future Hypotheses (Awaiting Further Experiments)
- Performance of 70B+ parameter models on prerequisite directionality.
- Portability of the reading-order prior to non-linear educational corpora (e.g., modular open online course modules or hypertext).
- Real-world pedagogical utility in computerized adaptive testing environments.
