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

## Status of the coefficients (baseline, kept unchanged)

Origin: a single expert pairwise-comparison matrix (Saaty scale, steps 1–3 above), not estimated from data. Intended
meaning of the factors: S = how similar the two concepts' meanings are, C = how often they are discussed together,
P = how close their chapters are, E = whether they are taught in the same educational context. These coefficients are
the `ahp` entry of `WEIGHTING_SCHEMES` in `educational_pipeline/relation_extractor.py` and remain the pipeline default.

The coefficients above are **expert judgements**. A consistency ratio of 0.022 shows that the pairwise judgements are
internally consistent; it says nothing about whether the resulting weight predicts anything. They are kept as the
documented baseline and are **not** claimed to be empirically optimal. Their measured behaviour is in
`kg_eval/README.md` (section 5.10): on AL-CPL query ranking the formula beats a random ranking, co-occurrence alone
does at least as well as the full formula, and S and P add nothing on their own.

## Implementation (corrected 2026-10-14)

Source of truth: `educational_pipeline/relation_extractor.py`: `pair_factors`, `combine`,
`RelationManager.finalize_weights`. Weights are computed **once, after all relations are collected**, because C and E
need the whole text. Each factor is in [0, 1]; the coefficients sum to 1, so the weight is in [0, 1].

### Factors

| Factor | Definition | Missing data |
|---|---|---|
| **S** (lexical overlap) | `|W_a ∩ W_b| / |W_a ∪ W_b|`, W = lowercase words of 3+ letters of the concept's definition **if the definition is validated** (`definition_is_valid`: the concept, by name or alias, is the subject of a defining clause "[a/an/the] X is/are/has/have/uses/refers to/means/is defined as ..." or "X: ...", after dropping a leading section-heading line), otherwise of the concept name. This is word overlap, not semantic understanding. | invalid/empty definition: name words (flag `definitions_valid` = both/one/none) |
| **C** (co-occurrence) | `min(1, n / 3)`, n = number of sentences that mention both concepts (name or alias, whole word, plural-tolerant). Sentence = the pipeline split after `.`, `?`, `!` inside each chunk, over the whole book. Undirected; independent of how many times any rule proposed the edge. | n = 0 |
| **P** (chapter proximity) | `1 / (1 + |k_a − k_b|)`, k = chapter number parsed from the chapter label of the concept's first mention (parsed textbook structure). Proximity is not evidence of a prerequisite. | either chapter unknown: 0.5 and `chapter_missing = True` |
| **E** (educational context) | Jaccard of the sets of parsed **sections** in which each concept is mentioned: how much the two concepts are taught in the same sections. Replaces the old constants. | a concept with no section label: 0 (counted in `edges_section_missing`) |

`weight = 0.52·S + 0.24·C + 0.09·P + 0.15·E`

Legacy values are kept for comparison in every row: `s_jaccard_raw` (S on unvalidated definitions),
`educational_context_legacy` (0.6 same chapter + 0.4 same section, else 0.3), and `weight_legacy` (the original
formula: raw S, `C = min(1, n_proposals/3)`, P, legacy E).

Why the changes (audit 2026-10-14, CK-12 baseline):
- **S:** only 43 of 130 concepts have a definition that passes validation (84 fail, 3 are empty). Most failures are real mis-assignments (e.g. Point ← the perpendicular-bisector theorem, Line ← a glide-reflection sentence); some are false rejections of genuine definitions (e.g. "Complementary angles are ..." for the concept *Complementary*). 34 of 93 edges had raw S = 1.0 because both concepts carried the *same* sentence. Validation removes that artefact; a MiniLM embedding cosine of the validated definitions is stored as `s_embedding` for comparison only.
- **C:** the old C counted *proposals* of the ordered pair, so one Similarity sentence counted twice (keyword-path bug 2) and repeated rule firings inflated it. It now counts sentences.
- **E:** over the 892 AL-CPL candidate pairs of the ranking evaluation, the old constants had Spearman 0.78 with P (both chapter-based); section-co-mention Jaccard has 0.28 with P but 0.78 with C.

### Weighting schemes (2026-10-15)

All schemes combine the same factors and are computed for every edge (`weight_ahp`, `weight_cooc_only`,
`weight_cooc_struct_a0.8` columns); `weight` is the scheme selected with `run_educational_pipeline(weighting_scheme=...)`,
default `ahp`, recorded in `weight_scheme`.

| Scheme | Formula | Status |
|---|---|---|
| `ahp` | 0.52 S + 0.24 C + 0.09 P + 0.15 E | expert baseline (default) |
| `cooc_only` | C | simplest data-supported alternative |
| `cooc_struct_a0.8` | 0.8 C + 0.2 E | alpha from CK-12 cross-validation; a candidate, not an established optimum, and not independent of the CK-12 evaluation |

Evaluation of all three: `kg_eval/README.md` section 5.11. Second-domain protocol: `kg_eval/second_domain_protocol.md`.

### Definitions used by S (2026-10-15)

`run_educational_pipeline(definition_policy="first_definitional")` (default) uses `definition_extractor.find_definition`:
a definition is the first sentence whose subject is the concept ("[A/An/The] X[ of ...] is/are/has/have/uses/refers
to/means/is defined as ..."), stored verbatim with `definition_kind = definitional`; otherwise only a mention is kept as
evidence (`definition_kind = mention`, empty definition). A later sentence never replaces a definitional one.
`definition_policy="legacy_longest"` reproduces the earlier behaviour (legacy extractor, longest definition wins), which
assigned mention sentences such as "If a line is parallel to one side ..." to Line.

### Extractor-supplied scores

| Extractor | Raw score | Handling |
|---|---|---|
| neural cross-encoder | `min(1, max(0.2, (logit + 2) / 7))` | stored as `extractor_scores` `neural:<x>`; **not** used as the weight (previously it replaced the formula) |
| LLM (`educationalPrompt`) | integer 1–10 | stored as `llm:<x>` (previously silently discarded because it was outside [0, 1]); not used as the weight |
| rules / keywords / `graph.csv` | none | — |

The two scales are not calibrated against each other or against the formula, so they are never combined; every edge
gets the formula weight, which makes weights comparable across sources. A non-numeric score is counted in the run's
relation stats (`invalid_extractor_score_<source>`), not dropped silently.

### Output columns (`relations.csv`)

| Column | Meaning |
|---|---|
| `weight` | formula weight with the corrected factors (`weight_source = ahp`) |
| `semantic_similarity`, `cooccurrence_count`, `chapter_proximity`, `educational_context` | corrected S, n (C = min(1, n/3)), P, E |
| `s_jaccard_raw`, `s_embedding`, `definitions_valid`, `chapter_missing`, `educational_context_legacy`, `weight_legacy` | legacy and diagnostic values (see above) |
| `n_proposals` | distinct (evidence sentence, source) proposals of this directed, typed edge |
| `sources` | extractors that proposed it: `rule`, `keyword`, `llm`, `neural`, `graph_csv` |
| `extractor_scores` | raw extractor scores, `source:value;...` |
| `evidence` / `evidence_all` | first evidence sentence / every distinct evidence sentence (` || `-separated) |
