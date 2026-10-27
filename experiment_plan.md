# Experiment Plan: Matrix, Priorities, and Completion Status

**Date:** 2026-10-23  
**Status:** Active Execution Matrix

---

## 1. Experiment Priority Matrix

| Exp ID | Title & Objective | Priority | Computational Cost | Dependencies | Completion Status | Deliverable / Output Artifact |
|---|---|---|---|---|---|---|
| **E1** | **Reproduction & Freezing of Baseline Results**<br>Verify all metrics on common covered set (868 pairs) across Rule, LLM, Hybrid, and Book Order. | **P0 (Critical)** | Low (Seconds) | `data_output/eval_framework/` | **COMPLETE** | `research_audit.md`, `prereq_eval_report.json` |
| **E2** | **Component Error Decomposition**<br>Deconstruct recall loss across: concept extraction $\to$ matching $\to$ candidate pairs $\to$ classification $\to$ closure. | **P0 (Critical)** | Low (Seconds) | `concepts_report.json`, `prereq_eval_report.json` | **COMPLETE** | Table in manuscript (§6), `claim_audit.md` |
| **E3** | **Structural-Prior & Component Ablation**<br>Isolate contribution of Reading Order alone, Co-occurrence alone, LLM relatedness alone, and combined Hybrid. | **P0 (Critical)** | Low (Seconds) | `weights_eval_report.json`, `hybrid.py` | **COMPLETE** | Table in manuscript (§6), `REPORT.md` §5 |
| **E4** | **Candidate-Pair Bottleneck Analysis**<br>Measure candidate recall against AL-CPL and evaluate upper-bound reachability under co-occurrence vs windowing. | **P1 (High)** | Low (Minutes) | `pairs.py`, `geometry.pairs` | **COMPLETE** | `data_output/ck12_geometry_kgx_v2/` analysis |
| **E5** | **Heuristic Weighting & AHP Ablation**<br>Paired NDCG@10 comparison of Saaty AHP vs $C$-only, $S$-only, $P$-only, $E$-only, and Book Order. | **P1 (High)** | Low (Seconds) | `weights_eval.py` | **COMPLETE** | Table in manuscript (§6), `ahp_weights.md` |
| **E6** | **Reference-Free Multi-Relation Diagnostics**<br>Quantify schema violations, taxonomic vs meronymic confusion, and cue-direction mismatch across all 5 relations. | **P1 (High)** | Low (Seconds) | `relation_checks.py` | **COMPLETE** | `relation_checks_report.json`, manuscript §6 |
| **E7** | **Prerequisite Retrieval (Gap Proxy) Evaluation**<br>Evaluate downstream retrieval of upstream prerequisite concepts from leaf concepts (P@5, NDCG). | **P2 (Medium)** | Low (Seconds) | `gap_proxy.py` | **COMPLETE** | `gap_proxy_report.json`, manuscript §8 |
| **E8** | **Multi-Model Scaling Matrix (3B, 7B, 14B)**<br>Evaluate parameter scaling on identical candidate set to test whether larger models overcome directional chance. | **P2 (Medium)** | High (Hours GPU/Ollama) | Ollama models, GPU RAM | **PENDING** (Marked as pending in revision; requires active Ollama daemon & multi-hour inference) |
| **E9** | **Second-Domain Replication (Physics)**<br>Replicate full pipeline on OpenStax Physics with AL-CPL Physics to test cross-domain generalization. | **P2 (Medium)** | High (Textbook extraction + Ollama run) | OpenStax Physics text, AL-CPL Physics | **PENDING** (Protocol frozen in `second_domain_protocol.md`; marked as future work) |
| **E10** | **Independent Multi-Relation Double Annotation**<br>Execute double annotation on 378-item blinded package to establish gold ground truth for 4 non-prereq types. | **P3 (Future)** | High (Human annotators) | 2 independent subject-matter annotators | **PREPARED** (`annotation_kit.py` created 378 items; adjudication pending human annotators) |

---

## 2. Decision on Pending High-Cost Experiments (E8, E9, E10)

In strict adherence to **Rule 3.1 (Never Fabricate Evidence)** and **Rule 3.4 (Inspect Before Implementing)**:
1. **Experiments E1 through E7** are **fully verified, mathematically consistent, reproducible from existing artifacts, and documented in detail**.
2. **Experiments E8 (Multi-Model Scaling), E9 (Second-Domain Replication), and E10 (Multi-Annotator Study)** are long-running external processes requiring dedicated GPU inference or human annotators.
3. Therefore, in the revised conference manuscript:
   - **E1–E7 constitute the solid, verified empirical core of the submission.**
   - **E8, E9, and E10 are explicitly and honestly demarcated** under Threats to Validity / Limitations, rather than filled with fabricated numbers or omitted silently.
   - The manuscript title and claims are appropriately and defensibly scoped to match the verified evidence.
