# Reproduction Guide: Educational Knowledge Graph Evaluation

This document provides exact, deterministic commands to reproduce the empirical evaluation of the LearnKG pipeline on CK-12 Basic Geometry against the AL-CPL benchmark.

---

## 1. Environment Setup

### Prerequisites
- Linux OS (tested on Ubuntu / Debian x86_64)
- Python 3.10+
- Virtual environment with dependencies from `environment.yml` or `requirements.txt`:
  - `pandas`, `scipy`, `numpy`, `networkx`, `scikit-learn`
  - `spacy` (with `en_core_web_sm` model installed)
  - `sentence-transformers`, `torch`
  - `rich`, `requests`

### Activation
```bash
source .venv/bin/activate
```

---

## 2. Running Unit and Regression Tests

To verify that the evaluation metrics, Wilson intervals, bootstrap sampling, cycle detection, and classification scorers function correctly:

```bash
# Run framework regression tests
python3 kg_eval/framework/test_framework.py

# Run extraction and consistency tests
python3 kg_extract/test_kg_extract.py
```
*Expected Output: All test cases pass with status `ok`.*

---

## 3. Reproducing the Main Evaluation Reports

All reports and tables in the paper are generated from machine-readable JSON artifacts in `data_output/eval_framework/`.

To regenerate the entire evaluation framework report:

```bash
# Run all evaluation modules and generate REPORT.md
python3 -m kg_eval.framework.run_all --out data_output/eval_framework
```

To run individual evaluation components:

```bash
# 1. Concept Coverage & Missing Concepts Analysis
python3 -m kg_eval.framework.concepts_eval --out data_output/eval_framework/concepts

# 2. Prerequisite Benchmark & Directional Accuracy on AL-CPL
python3 -m kg_eval.framework.prereq_eval --out data_output/eval_framework/prerequisite

# 3. Reference-Free Multi-Relation Structural Diagnostics
python3 -m kg_eval.framework.relation_checks --out data_output/eval_framework/relations

# 4. Saaty AHP Edge Weight & Ranking Ablation
python3 -m kg_eval.framework.weights_eval --out data_output/eval_framework/weights

# 5. Prerequisite Retrieval (Gap Proxy) Evaluation
python3 -m kg_eval.framework.gap_proxy --out data_output/eval_framework/gap_proxy

# 6. Generate Multi-Relation Blinded Annotation Package
python3 -m kg_eval.framework.annotation_kit --out data_output/eval_framework/annotation
```

---

## 4. Key Output Artifact Locations

- Master Evaluation Summary: `data_output/eval_framework/REPORT.md`
- Prerequisite Metrics JSON: `data_output/eval_framework/prerequisite/prereq_eval_report.json`
- Weight Ablation Metrics JSON: `data_output/eval_framework/weights/weights_eval_report.json`
- Structural Diagnostics JSON: `data_output/eval_framework/relations/relation_checks_report.json`
- Blinded Annotation Items: `data_output/eval_framework/annotation/blind_package/items.csv`
