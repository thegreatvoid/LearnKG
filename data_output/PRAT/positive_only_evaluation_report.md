# PRAT Positive-Only Prerequisite Evaluation Report

## Summary
- **Dataset**: PRAT
- **Protocol**: Positive-Only Evaluation (Zero synthetic negatives)
- **Gold Concepts**: 133 (Mapped: 53, 39.9%)
- **Gold Pairs**: 384 unique (Evaluable subset: 72, 18.8%)
- **Predicted Prerequisite Pairs**: 0 (Deduplicated)

## Metrics Table
| Metric | Evaluable Subset (Both Mapped) | Full Gold Set |
|---|---|---|
| True Positives (TP) | 0 | 0 |
| Unmatched Predictions (FP)* | 0 | 0 |
| False Negatives (FN) | 72 | 384 |
| **Precision** | **0.0000** | **0.0000** |
| **Recall** | **0.0000** | **0.0000** |
| **F1-Score** | **0.0000** | **0.0000** |
| **Gold-Pair Coverage** | **0.0000** | **0.0000** |

> \* *Important qualification*: In positive-only evaluation, unmatched predictions are treated as FP relative to the gold set, but cannot be confirmed as false pedagogical dependencies because the benchmark is not an exhaustive negative annotation. ROC-AUC and specificity are omitted.
