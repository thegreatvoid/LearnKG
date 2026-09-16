# AHP Edge Weight Derivation

## Formula

$$\text{weight} = 0.52 \cdot S + 0.24 \cdot C + 0.09 \cdot P + 0.15 \cdot E$$

| Symbol | Factor | AHP Weight | Source in Code |
|---|---|---|---|
| **S** | Semantic Similarity | 0.52 | LLM-assigned `weight` (1–10), normalised to [0,1] |
| **C** | Co-occurrence | 0.24 | Chunk co-occurrence count, normalised (cap at 5) |
| **P** | Chapter Proximity | 0.09 | Jaccard overlap of node chunk-id sets (0–1) |
| **E** | Educational Context | 0.15 | 1 if relationship predicate contains educational keyword, else 0 |

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

### Factor Derivation in Code

| Factor | How it is computed |
|---|---|
| **S** | `(llm_weight - 1) / 9.0` — normalises LLM score from [1,10] → [0,1] |
| **C** | `cooccurrence_count / 5.0` — normalises count, capped at 5 |
| **P** | Jaccard index: `|shared_chunks| / |union_chunks|` between source & target node chunk sets |
| **E** | `1.0` if relationship contains any of: *prerequisite, explains, defines, enables, introduces, requires, extends, generalizes, specializes, applies, illustrates, teaches* |

### Output

- Raw AHP score: **[0, 1]** — stored as `weight` column
- Display weight: **[1, 10]** — stored as `weight_display`, used for Pyvis edge thickness
- Edge tooltip shows: `AHP: 0.XXX | <description>`
- Edge label shows: `0.XX` (AHP score)
