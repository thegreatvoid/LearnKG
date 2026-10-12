# AHP Edge Weight Derivation

## Formula

$$\text{weight} = 0.52 \cdot S + 0.24 \cdot C + 0.09 \cdot P + 0.15 \cdot E$$

| Symbol | Factor | AHP Weight | Source in Code |
|---|---|---|---|
| **S** | Semantic Similarity | 0.52 | Jaccard overlap of the concepts' definition words (0–1) |
| **C** | Co-occurrence | 0.24 | `min(1, cooccurrence_count / 3)` |
| **P** | Chapter Proximity | 0.09 | `1 / (1 + chapter distance)`; 0.5 if a chapter is unknown |
| **E** | Educational Context | 0.15 | 0.6 same chapter + 0.4 same section; 0.3 if neither |

Details in [Implementation](#implementation).

---

## Step 1 — Pairwise Comparison Matrix (Saaty 1–9 scale)

|       | S    | C    | P   | E    |
|-------|------|------|-----|------|
| **S** | 1    | 3    | 5   | 3    |
| **C** | 1/3  | 1    | 3   | 2    |
| **P** | 1/5  | 1/3  | 1   | 1/2  |
| **E** | 1/3  | 1/2  | 2   | 1    |

## Step 2 — Geometric Mean Weights

| Factor | Row Product | 4th Root | Normalised Weight |
|---|---|---|---|
| S | 1×3×5×3 = 45 | 2.590 | **0.52** |
| C | (1/3)×1×3×2 = 2 | 1.189 | **0.24** |
| P | (1/5)×(1/3)×1×(1/2) = 0.033 | 0.427 | **0.09** |
| E | (1/3)×(1/2)×2×1 = 0.333 | 0.760 | **0.15** |

## Step 3 — Consistency Check

- **λ_max** ≈ 4.06
- **CI** = (4.06 − 4) / 3 = 0.02
- **RI** (n=4) = 0.90
- **CR** = 0.02 / 0.90 ≈ **0.022** ✅ (< 0.10 threshold — consistent)

---

## Implementation

Source of truth: `educational_pipeline/relation_extractor.py` (`ahp_components`, `calculate_ahp_weight`).
The factors are lightweight, dependency-free proxies, each normalised to [0, 1]; the four AHP weights sum to 1,
so the edge weight is in [0, 1].

### Factor Derivation in Code

| Factor | How it is computed |
|---|---|
| **S** | Jaccard overlap of the two concepts' definition word sets (falls back to the concept name if a definition is empty). A proxy for embedding cosine similarity. |
| **C** | `min(1, cooccurrence_count / 3)`, where `cooccurrence_count` is how many times the ordered concept pair has been extracted so far (sentence-level co-mentions, rule/LLM/neural extractions). |
| **P** | `1 / (1 + |chapter_a - chapter_b|)`, using the number parsed from the chapter label (e.g. `"Chapter 5: ..."` gives 5); 0.5 if either chapter is unknown. Chapter/section are taken from the concept's first mention. |
| **E** | `0.6` if both concepts are in the same chapter, plus `0.4` if they are in the same section; `0.3` if neither matches. |

An extractor may supply its own weight in [0, 1] (e.g. the neural prerequisite extractor). That value is used
instead of the formula (`weight_source = "provided"`). Weights outside [0, 1] (such as raw 1-10 LLM scores) are
ignored and the formula is used. When the same edge is extracted again, the higher weight is kept.

### Output columns (`relations.csv`)

| Column | Meaning |
|---|---|
| `weight` | Final edge weight in [0, 1] |
| `weight_source` | `ahp` (formula) or `provided` (extractor-supplied). Weighting ablations are only valid on `ahp` edges. |
| `cooccurrence_count` | Raw pair count behind **C** (before the `/3` cap) |
| `semantic_similarity`, `chapter_proximity`, `educational_context` | Factors S, P, E for the stored edge, so the weight can be recomputed and ablated exactly |

