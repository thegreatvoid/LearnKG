# kg_eval: evaluation of the educational KG (GAPGRAPH)

Handoff document: everything needed to continue this work on another machine or in another Claude Code instance without the original chats. Work done 2026-10-11 to 2026-10-13 (four sessions). Section 5 holds every result with the file it came from; section 9 is the plan; section 10 is the "where to start" checklist.

## 1. Context

- Project: `LearnKG/` builds an educational knowledge graph from a textbook. Test book: CK-12 Basic Geometry (`data_input/ck12_geometry/ck12_basic_geometry_concepts.txt`, 21 KB, 12 chapters, 59 numbered sections).
- Two extraction pipelines exist:
  - `educational_pipeline/` (entry point `run_pipeline.py --pipeline educational`): rule-based + optional LLM (Ollama) + neural prerequisite extractor. **Tuned to the test book** (hard-coded geometry vocabulary and regex rules, caveat 4), so it is kept only as a baseline.
  - `kg_extract/` (entry point `python -m kg_extract.run`): the current approach. Grounded, domain-agnostic concept extraction, candidate pairs, LLM pair scoring; plus `kg_extract/hybrid.py`, which rebuilds the graph from a finished run using textbook order and text signals. Details in `kg_extract/README.md`.
- All KGs of the book that have been evaluated (all under `data_output/`; each has its reports in `<folder>/kg_eval/`):

| Folder | How it was made | Concepts / edges / Prerequisite edges |
|---|---|---|
| `ck12_geometry/` | `educational_pipeline`, no LLM (rules + neural extractor). Predates the chapter/section fix (caveat 1). | 130 / 90 / 34 |
| `ck12_geometry_colab/` | `educational_pipeline` on Colab with Ollama `zephyr:latest` (+ neural extractor) | 209 / 364 / 118 |
| `ck12_geometry_kgx_run1/` | `kg_extract`, `qwen2.5:7b-instruct`, before the parser fix and before the concept noise filters | 209 / 612 / 81 |
| `ck12_geometry_kgx_run2/` | Same settings as run 1. Scores identical to run 1 (temperature 0 is deterministic) | 209 / 611 / 81 |
| `ck12_geometry_kgx_hybrid/` | `kg_extract.hybrid` on run 1. **Uses book order** | 209 / 773 / 562 |
| `ck12_geometry_kgx_v2/` | `kg_extract` after the parser fix and the concept noise filters, `qwen2.5:7b-instruct` on Colab T4, 2026-10-13 | 204 / 545 / 54 |
| `ck12_geometry_kgx_v2_hybrid/` | `kg_extract.hybrid` on v2, run locally (no LLM calls). **Uses book order**. Best graph so far | 204 / 669 / 518 |

- Edge weight in `educational_pipeline` = `0.52*S + 0.24*C + 0.09*P + 0.15*E` (AHP-derived), see `docs/ahp_weights.md` and `educational_pipeline/relation_extractor.py`. Range [0, 1].
  - S = Jaccard overlap of the concepts' definition words (a proxy for semantic similarity, NOT embeddings)
  - C = `min(1, cooccurrence_count/3)`
  - P = `1/(1+chapter_distance)`, 0.5 if either chapter is unknown (was constant 1.0 in `ck12_geometry/` and `ck12_geometry_colab/`, caveat 1)
  - E = 0.6 same chapter + 0.4 same section, 0.3 if neither (the +0.4 never fired in those two KGs, caveat 1)
  - Edges with `weight_source=provided` (LLM- or neural-extractor-supplied weight) bypass the formula.
  - `kg_extract` edges carry `weight_source=llm_score` (the LLM vote share); hybrid edges carry the hybrid score.
- Target construct for the weight (decided with the user): **educational relevance for localized graph construction**, NOT factual confidence.
- Relation ontology (5 types) as defined by the pipeline (`relation_extractor.py` header, `helpers/prompts.py` `educationalPrompt`):
  - Prerequisite: A → B, A must be understood before B
  - Part-of: A is a component of B
  - Application: A is applied/used in B
  - **Extension: A builds upon / extends B (so A comes later than B)**
  - Similarity: undirected in meaning
- Constraint decided by the user: **the evaluation plan must not involve human annotation** (section 9). Hand readings of output in this file are labelled as such and are not used as metrics.

## 2. State of the code (2026-10-13)

All code changes are committed on branch `ACL` (pushed to `origin/ACL`). Only these are untracked and should be committed so another machine has them: `data_output/ck12_geometry_kgx_v2/` and `data_output/ck12_geometry_kgx_v2_hybrid/` (the v2 outputs and all their reports).

| Commit | What |
|---|---|
| `650fc8e`, `7078785` | LLM-as-judge (Parts A–C), `relations.csv` weight columns, `docs/ahp_weights.md` |
| `fcf125f` | `prereq_gold.py` (AL-CPL), `book_order.py`, `data.py` helpers, `helpers/prompts.py` `import re` fix, Colab zephyr KG |
| `a751fbc` | `kg_extract/` pipeline (grounded concepts, pair generation, pair scoring, consistency), `concept_quality.py` |
| `4ff1bd5` | Chapter/section fixes in `educational_pipeline` (caveat 1): P was always 1.0, sections never detected, wrong chapter labels; docs fixed |
| `e41b508` | `kg_extract/hybrid.py`, `--dump-intermediate`, runs 1/2 and run 1 hybrid with reports |
| `689a371` | `kg_extract` concept noise filters, `concept_candidates.csv`, LLM concept-precision judge in `concept_quality.py`, tests |

Notes:
- `kg_extract` reuses `educational_pipeline`'s parser, structure detector and chunker, so the parser fix in `4ff1bd5` also changed `kg_extract` input: section headings are now detected (run 1 had none). v2 differs from run 1 in both the parser fix and the concept filters; their effects are not separated.
- `data_output/ck12_geometry/` and `ck12_geometry_colab/` were built before `4ff1bd5` and have not been regenerated.
- The local `.venv` (Windows, Python 3.11) was repaired on 2026-10-12: 28 packages had their files deleted with folders left behind (alphabetically `aiofiles`…`flatbuffers`, plus pillow, python-dotenv, PyYAML, setuptools), which broke spaCy. They were force-reinstalled at their recorded versions; `en_core_web_sm` 3.8.0 and `wordfreq` 3.1.1 were installed. `sentence-transformers` is NOT installed in the venv (needed by `judge.py` and `bigs.py`). Some langchain version conflicts pre-exist. Ollama is not installed locally; LLM work runs on Colab.
- Run Python through the venv: `.venv/Scripts/python.exe` on Windows. The system Python lacks spaCy and `wordfreq`.

## 3. Code layout (`kg_eval/`)

| File | Role | Needs LLM? |
|---|---|---|
| `data.py` | loading (+ layout adapter), sentence split, text-position helpers, AL-CPL loader, Spearman/AUC/AP/PRF/bootstrap helpers | no |
| `prereq_gold.py` | **Section 1**: prerequisite correctness vs AL-CPL gold, with text baselines; also scores `pair_scores.csv` as `kg_pairscore` when present | no |
| `book_order.py` | **Section 2**: edge direction vs textbook teaching order | no |
| `concept_quality.py` | Concept extraction: verbatim-in-text rate, AL-CPL concept recall, how many gold positive pairs the pair generator considered; optional `--judge-model` LLM concept precision | only with `--judge-model` |
| `judge.py` | LLM judge via Ollama (`/api/chat`, JSON-schema output, temperature 0). Env: `OLLAMA_JUDGE_MODEL`, `OLLAMA_HOST`. Each edge judged against top-8 retrieved textbook sentences (MiniLM). Cache keys include model name. Retries 3x. | yes |
| `bigs.py` | BIGS (Lermanda, Ojeda, Reutter, ESWC 2026). BIGS→ = mean over textbook sentences of min cosine distance to a verbalized triple; BIGS← = mean over triples of min distance to a sentence; Sym-BIGS = 1 − harmonic mean of (1−BIGS→),(1−BIGS←). Embedder `all-MiniLM-L6-v2`. Lower is better. | no |
| `source_quality.py` | Part A (judged support, BIGS, coverage, structure) | partly |
| `weight_validity.py` | Part B: `sample`, `rate`, `analyze` | yes |
| `weight_ablation.py` | Part C | uses Part B ratings |

### Running

From `LearnKG/` (Windows venv: `.venv/Scripts/python.exe`, Linux/macOS venv: `.venv/bin/python`).

LLM-free (seconds each). `--kg-dir` = any folder with `concepts.csv` + `relations.csv`; `--out` defaults to `<kg-dir>/kg_eval`; `--source` overrides the textbook `.txt`:

```
python -m kg_eval.prereq_gold     --kg-dir data_output/ck12_geometry_kgx_v2
python -m kg_eval.concept_quality --kg-dir data_output/ck12_geometry_kgx_v2
python -m kg_eval.book_order      --kg-dir data_output/ck12_geometry_kgx_v2     # NOT on hybrid KGs (they use book order)
python -m kg_extract.hybrid --run data_output/ck12_geometry_kgx_v2 --out data_output/ck12_geometry_kgx_v2_hybrid   # no LLM
python kg_extract/test_kg_extract.py                                             # offline unit tests (10)
```

With an LLM (Colab, section 7):

```
python -m kg_extract.run --data-dir ck12_geometry --model qwen2.5:7b-instruct --hubs 10 --samples 2 --out data_output/<run>
python -m kg_eval.concept_quality --kg-dir data_output/<run> --judge-model llama3.1:8b --subject geometry
```

Older LLM-judge parts (slow on CPU, ~30-45 s per call with a 3B model):

```
export OLLAMA_JUDGE_MODEL=qwen2.5:3b-instruct
python -m kg_eval.source_quality
python -m kg_eval.weight_validity sample && python -m kg_eval.weight_validity rate --reps 1 && python -m kg_eval.weight_validity analyze
python -m kg_eval.weight_ablation
```

Outputs in `<kg-dir>/kg_eval/`: `prereq_gold_report.json`, `prereq_gold_pairs.csv`, `book_order_report.json`, `book_order_edges.csv`, `concept_quality_report.json`, `concept_judgments.csv`, `concept_judge_cache.jsonl`, `*_report.json`, `support_judgments.csv`, `weight_sample.csv`, `judge_cache.jsonl`. A `kg_extract` run folder also has `run_meta.json` (settings, timing, counters, LLM success counts), `concept_candidates.csv` (every candidate concept, its cues, salience and drop reason; v2 onward) and `pair_scores.csv`. The 3B-judge results are archived in `data_output/ck12_geometry/kg_eval_qwen2.5-3b/`.

## 4. Methodology

### Section 1: prerequisite correctness vs AL-CPL (`prereq_gold.py`)

- Gold: **AL-CPL** geometry (Liang et al., AAAI 2018; https://github.com/harrylclc/AL-CPL-dataset), files `data_input/ck12_geometry/geometry.pairs` (1681 labelled pairs) and `geometry.preqs` (524 positives). A line `A,B` means **B is a prerequisite of A** (dataset README: "predict whether the 2nd concept is a prerequisite of the 1st"). It is recovered by a KG edge `B → A`.
- Gold concept names (Wikipedia titles) are matched to KG concepts with `match_gold_concept` from `evaluate_prerequisite_extraction.py` (synonym map → exact → plural → token → fuzzy). Low-confidence matches are listed in the report.
- **Direction is strict.** A KG edge pointing the wrong way counts as wrong. `evaluate_prerequisite_extraction.py` counts reversed edges as true positives (`extracted_pred = directed_pred or reversed_pred`), so its numbers are inflated; do not report them.
- Predictors (all scored on the same pairs; score > 0 = predicted positive):
  - `kg_prereq` Prerequisite edge B → A, score = weight
  - `kg_closure` B reaches A via Prerequisite edges, score = 1/path length **[main result for hybrid KGs]**
  - `kg_pairscore` the run's pair score for B → A over every pair (`pair_scores.csv`); the fair ranking comparison with baselines
  - `kg_any_relation` any relation type B → A
  - `kg_undirected` Prerequisite either direction (diagnostic only)
  - `book_order` B first mentioned before A in the book
  - `cooccurrence` sentence co-occurrence count (undirected)
  - `cooc_x_order` co-occurrence, only when B precedes A
  - `refd_text` RefD (Liang et al. 2015) adapted to textbook sentences: `|S_A∩S_B|/|S_A| − |S_A∩S_B|/|S_B|`
- Evaluation sets: **main** = pairs where both concepts matched to distinct KG concepts and both located in the text (all predictors comparable); **end_to_end** = all 1681 pairs, unmatched = "no edge" (KG predictors only). The main set differs between KGs (it depends on which gold concepts match), so cross-KG comparisons on it are not paired; end_to_end is the same 1681 pairs for every KG.
- Metrics: precision, recall, F1, MCC, ROC-AUC, PR-AUC (average precision); bootstrap 95% CI over pairs for F1 and AUC; "weight-only" AUC among pairs that have a KG edge.

### Section 2: direction vs textbook order (`book_order.py`)

- Position of a concept = first whole-word, case-insensitive, plural-tolerant mention of its name or aliases in the textbook. Also at section granularity (numbered sections like `1.2`; same section = tie).
- Expected direction: **Prerequisite → forward** (source mentioned first); **Extension → backward** (pipeline defines "source extends target"); other types have no expected direction.
- Metrics: forward rate per relation type with bootstrap CI and two-sided binomial test vs 0.5; Prerequisite closure agreement (all u ⇝ v pairs); Kendall τ-b of prerequisite depth vs position; weight AUC for "edge points forward"; **reference**: forward rate of AL-CPL gold positives (90%) and negatives (32%) in this book, which is the realistic ceiling.
- **Circularity:** hybrid KGs use book order (`run_meta.json` → `uses_book_order: true`), so this check is trivially satisfied for them on this book. Report it only for non-hybrid KGs, or against a *different* textbook (plan, step 4).

### Concept quality (`concept_quality.py`)

- Verbatim rate: share of concept names found in the textbook (plural-tolerant). 1 − rate = hallucination rate.
- AL-CPL concept recall: share of the 89 AL-CPL geometry concepts that match a KG concept (any confidence / high confidence).
- Candidate recall upper bound: of the gold positive pairs whose two concepts both exist in the KG, the share the pair generator put in `pair_scores.csv` (or `candidate_pairs.csv`). The LLM can only score pairs that are generated.
- Precision (optional, `--judge-model`): an Ollama model labels every concept, given its evidence sentence, as `concept` / `not_concept` / `duplicate` (batches of 25, JSON schema). Precision = share labelled `concept`. Cached in `concept_judge_cache.jsonl` by model, subject and name. Use a model different from the extractor's. **Not validated yet: see 5.6.**

### Parts A–C (LLM-judge based, first session)

- **A. Source-grounded quality**: judged support (Supported / Contradicted / Insufficient evidence / Ambiguous + quote), BIGS, coverage, structural checks (duplicates, invalid refs, malformed rows, self-loops, cycles in Prerequisite and Part-of).
- **B. Weight validity**: stratified sample (relation type × weight tercile); blind LLM rating 1–5 of educational importance ("1 = trivial or misleading link … 5 = essential"; the judge sees names, relation type and definition, the evidence sentence and 8 retrieved sentences, not the weight); Spearman ρ overall and per type with bootstrap CI; weight tiers compared. The 1–5 scale has no documented rationale; Spearman/AUC are rank-based, so it need not match the [0, 1] weight scale.
- **C. Ablation**: edges frozen, only the weight function varies (uniform, single components, leave-one-out, full AHP, tuned on dev). Spearman vs rating, AUC for rating ≥ 4, paired bootstrap. Split: chapters 1–6 dev, 7–12 held-out. The tuned variant is fitted to the same LLM ratings it is scored on (dev split only), so it is partly circular.
- Status: B and C are **retired as primary evidence** (LLM ratings collapsed to almost all 3s and 4s); they are to be replaced by AL-CPL-based weight evaluation (plan step 1.2).

## 5. Results (CK-12 Basic Geometry)

### 5.1 Headline (as of 2026-10-13)

- **Best KG: `ck12_geometry_kgx_v2_hybrid`.** Transitive Prerequisite F1 vs AL-CPL 0.768 [0.725, 0.804] (P 0.833, R 0.713), above the textbook-order baseline 0.712 [0.673, 0.748]. CIs overlap: suggestive, not established. Paired comparison with the run 1 hybrid on all 1681 pairs (end_to_end): closure F1 0.539 vs 0.529, a small gain.
- **The LLM pair vote alone has no prerequisite signal.** Plain v2: ROC-AUC 0.50, 4 of 293 gold prerequisites recovered; same as runs 1/2. The hybrid's lift comes from book order, co-occurrence and RefD; the LLM only contributes a relatedness signal there.
- **LLM edge direction is wrong.** Plain v2 Prerequisite edges point forward 40% of the time vs 90% for true prerequisites.
- **Concept noise is gone** ("times", "states", "sum", "half", "sides", "remote", chapter titles), concept recall 0.76 → 0.73, and the pair generator now covers 52% of gold positive pairs (run 1: 35%).
- **The concept-precision judge is unreliable** (llama3.1:8b): reports 0.81, but rejects obvious concepts and finds no duplicates (5.6).
- Visual report of the v2 evaluation (private claude.ai artifact, owner only): https://claude.ai/code/artifact/590239dd-5923-41a4-b185-8dff12fd7639. Everything in it is reproduced in 5.4–5.7.

### 5.2 `educational_pipeline` KGs side by side (sections 1 and 2)

Source: `data_output/ck12_geometry{,_colab}/kg_eval/{prereq_gold,book_order}_report.json`.

| | Rule-based (`ck12_geometry`) | Ollama zephyr (`ck12_geometry_colab`) |
|---|---|---|
| Concepts / relations / Prerequisite edges | 130 / 90 / 34 | 209 / 364 / 118 |
| AL-CPL concepts matched to KG | 65 / 89 | 69 / 89 |
| Main-set pairs (prevalence) | 1017 (0.286) | 1128 (0.281) |
| **AL-CPL** Prerequisite precision | 0.58 | 0.42 |
| Recall | 0.024 | 0.016 |
| F1 [95% CI] | 0.05 [0.02, 0.09] | 0.03 [0.01, 0.06] |
| ROC-AUC [95% CI] | 0.51 [0.50, 0.52] | 0.50 [0.50, 0.51] |
| Gold pairs with any Prerequisite edge | 12 | 12 |
| Gold positives with edge pointing the wrong way | 2 | 3 |
| Weight-only AUC (pairs with an edge) | 0.60 (n=12) | 0.37 (n=12) |
| *Baseline book_order: F1 / AUC* | *0.71 / 0.86* | *0.69 / 0.85* |
| *Baseline refd_text: F1 / AUC* | *0.42 / 0.68* | *0.41 / 0.67* |
| *Baseline cooc_x_order: F1 / AUC* | *0.45 / 0.64* | *0.43 / 0.63* |
| **Book order**: Prerequisite forward rate, char [CI] | 0.58 [0.39, 0.74], p=0.47 | 0.47 [0.36, 0.59], p=0.64 |
| Prerequisite forward rate, section | 0.54, p=0.85 | 0.34, p=0.03 (significantly *backward*) |
| Prerequisite edges with an endpoint not found in the book | 0 / 34 | 37 / 118 |
| Prerequisite closure agreement | 0.53 | 0.50 |
| Kendall τ-b (depth vs position) | −0.04 (p=0.71) | −0.03 (p=0.70) |
| Weight AUC for "points forward" | 0.48 | 0.49 |
| Extension edges forward / backward (should be backward) | 1 / 1 | 1 / 8 |
| *Reference: AL-CPL gold positives pointing forward* | *0.90* | *0.90* |

Interpretation:
1. Both KGs are at chance on AL-CPL (AUC ≈ 0.5). Edges that exist are better than the base rate (precision 0.58 / 0.42 vs prevalence 0.29), but almost no gold pairs get an edge.
2. Ollama tripled the number of edges but hit the same 12 gold pairs, with lower precision.
3. Ollama's Prerequisite edges lean backward (34% forward at section level, vs 90% for true prerequisites).
4. A third of Ollama's Prerequisite edges use concept names that do not occur in the book (e.g. "Triangle Congruence using AAS" → "Triangle Congruence using ASA").
5. Weights carry no signal in either KG.
6. Rule-based backward edges are mostly part→whole mislabelled as Prerequisite (e.g. `Chord → Circle`, `Angle Bisector → Angle`).
7. `weight_source=provided` mixes Ollama and neural-extractor edges, so the Ollama run cannot be attributed to Ollama alone.

### 5.3 Parts A–C (rule-based KG, judge = qwen2.5:3b-instruct, weak)

- Structural: all clean (0 duplicates, invalid refs, malformed, self-loops, cycles).
- Coverage: 61/130 concepts (47%) appear in any edge; 0/24 hand-written gold pairs (`data_input/ck12_geometry/gold_pairs.csv`) recovered with direction (2/24 ignoring direction).
- BIGS: BIGS→ 0.466, BIGS← 0.283, Sym-BIGS 0.388.
- Judged support (88 of 90 edges): Supported 60%, Insufficient 26%, Contradicted 14%. Not validated.
- B: overall ρ 0.05 (95% CI −0.16 to 0.26, n=90). Judge rated 58/90 edges as 4 and 29 as 3: no variance, uninformative.
- C: no weight variant correlates with ratings (held-out ρ −0.12 to +0.19, all noise).

### 5.4 `kg_extract` KGs vs AL-CPL (section 1)

Source: `data_output/<folder>/kg_eval/prereq_gold_report.json`, `main` set unless noted. Baselines are computed per KG on its own main set; the v2 baselines are shown (run 1's are within 0.01).

| KG (main-set pairs, prevalence) | Predictor | P | R | F1 [95% CI] | ROC-AUC [95% CI] |
|---|---|---|---|---|---|
| run 1 (1061, 0.290) | kg_prereq | 0.556 | 0.016 | 0.032 [0.007, 0.066] | 0.505 [0.499, 0.514] |
| | kg_closure | 0.538 | 0.023 | 0.044 [0.013, 0.082] | 0.507 [0.499, 0.518] |
| | kg_pairscore | 1.000 | 0.003 | 0.006 | 0.504 [0.496, 0.514] |
| run 1 hybrid (1061, 0.290) | kg_prereq | 0.902 | 0.179 | 0.298 [0.239, 0.353] | 0.585 [0.565, 0.606] |
| | kg_closure | 0.862 | 0.649 | 0.741 [0.697, 0.782] | 0.806 [0.777, 0.836] |
| | kg_pairscore | 0.870 | 0.130 | 0.226 [0.172, 0.281] | 0.872 [0.849, 0.893] |
| **v2** (989, 0.296) | kg_prereq | 0.444 | 0.014 | 0.026 [0.006, 0.052] | 0.503 [0.497, 0.511] |
| | kg_closure | 0.417 | 0.017 | 0.033 [0.007, 0.062] | 0.504 [0.495, 0.511] |
| | kg_any_relation | 0.330 | 0.102 | 0.156 [0.106, 0.201] | 0.506 [0.487, 0.526] |
| | kg_pairscore | 0.000 | 0.000 | 0.000 | 0.502 [0.494, 0.509] |
| **v2 hybrid** (989, 0.296) | kg_prereq | 0.843 | 0.256 | 0.393 [0.332, 0.452] | 0.619 [0.594, 0.644] |
| | **kg_closure** | 0.833 | 0.713 | **0.768 [0.725, 0.804]** | 0.827 [0.799, 0.853] |
| | kg_pairscore | 0.927 | 0.130 | 0.228 [0.167, 0.284] | **0.874 [0.849, 0.894]** |
| baselines on v2 pairs | book_order | 0.570 | 0.949 | 0.712 [0.673, 0.748] | 0.855 [0.831, 0.877] |
| | cooc_x_order | 0.744 | 0.297 | 0.424 [0.362, 0.482] | 0.627 [0.600, 0.655] |
| | refd_text | 0.727 | 0.273 | 0.397 [0.337, 0.456] | 0.664 [0.638, 0.691] |
| | cooccurrence | 0.377 | 0.317 | 0.344 [0.293, 0.395] | 0.549 [0.518, 0.582] |

End_to_end (same 1681 pairs for every KG, unmatched = no edge), F1 / ROC-AUC:

| KG | kg_prereq | kg_closure | kg_pairscore |
|---|---|---|---|
| run 1 | 0.019 / 0.503 | 0.026 / 0.504 | 0.004 / 0.502 |
| run 1 hybrid | 0.188 / 0.550 | 0.529 / 0.678 | 0.140 / 0.700 |
| v2 | 0.015 / 0.502 | 0.019 / 0.502 | 0.000 / 0.501 |
| v2 hybrid | 0.245 / 0.566 | 0.539 / 0.681 | 0.135 / 0.692 |

Other v2 facts: 65 of 89 AL-CPL concepts matched; 4 gold positives have a v2 Prerequisite edge pointing the wrong way (v2 hybrid: 1); weight-only AUC v2 0.50 (n=9), v2 hybrid 0.64 (n=89).

Interpretation:
1. Without the hybrid step, `kg_extract`'s LLM pair votes are at chance, in every run. The pair score does not rank prerequisites above non-prerequisites.
2. The hybrid builder (book order × percentile rank of order gap, co-occurrence, RefD, LLM relatedness; top-3 related predecessors per concept) is what works. Its pair-score AUC (0.874) is at the textbook-order level (0.855); its transitive closure gives the best F1.
3. v2 hybrid vs run 1 hybrid: higher recall (0.71 vs 0.65) at slightly lower precision; paired end_to_end closure F1 0.539 vs 0.529. The gain is small and may come from the parser fix, the concept filters, or both.

### 5.5 Concepts (`concept_quality.py`)

Sources: `data_output/<folder>/kg_eval/concept_quality_report.json`, `<folder>/run_meta.json`, `<folder>/concept_candidates.csv`.

| Run | Concepts | Verbatim | AL-CPL concept recall (any / high) | Gold positive pairs the generator considered |
|---|---|---|---|---|
| run 1 (LLM concepts, no filters) | 209 | 1.00 | 0.764 / 0.730 | 109 / 308 = 35% |
| v2 (LLM concepts, filters) | 204 | 1.00 | 0.730 / 0.708 | 152 / 293 = 52% |
| no-LLM, no filters (local test, 2026-10-12) | 194 | 1.00 | 0.708 / 0.685 | 36% |
| no-LLM, filters (local test, 2026-10-12) | 203 | 1.00 | 0.742 / 0.730 | 54% |

Both LLM runs: top-k 250, per-concept 8, hubs 10, max-pairs 1500, samples 2. v2 concept stage: 60/60 chunks through the LLM, 1061 candidates seen, dropped 68 lone common words, 20 common-word phrases, 19 below min frequency, 12 ungrounded.

Hand reading of v2 vs run 1 (not a metric):
- Removed noise: times, times height, pi times, states, theorem states, postulate states, sum, half, sides, pairs, products, remote, properties, relationships, relationships with triangles, rigid transformations, right triangle trigonometry, direction, statement, measure, length, interior, soh cah toa.
- Real terms lost: area, segment, similarity, leg, height, base, alternate interior angles, co-interior angles, congruent chords, inverse trigonometric functions, 30 60 90 triangle, 45 45 90 triangle. Mostly single common words that only a chapter title or spaCy proposed and the LLM did not name. AL-CPL concepts no longer matched include Sine, Similarity_(geometry), Inverse_trigonometric_functions, Parallel_(geometry).
- New noise: CK-12 Basic Geometry Concepts (book title), Lines Parallel (heading fragment), Obtuse, pi radius, bisect, vertex/vertices not merged (irregular plurals are not handled by the normalizer).

### 5.6 Concept-precision judge (v2, `llama3.1:8b`)

Source: `data_output/ck12_geometry_kgx_v2/kg_eval/concept_judgments.csv`, `concept_quality_report.json` → `precision`.

- 204 judged in 9 calls (all succeeded): 166 concept, 38 not_concept, 0 duplicate → reported precision 0.814.
- Hand reading (not a metric): about 10 of the 38 rejections hold up (CK-12 Basic Geometry Concepts, Lines Parallel, Obtuse, pi radius, bisect, protractor, bases, Solids, cross products, Tangents). Clear concepts it rejected: hypotenuse, kite, line, pentagon, sector, ratio, proportion, lateral area, Trigonometry, Supplementary angles, Inductive Reasoning, hypothesis, conclusion, midsegment of a triangle, Sine/Cosine/Tangent Ratios, intersection, distance between two points. It found no duplicates despite vertex/vertices. True precision is probably nearer 0.95.
- Conclusion: the judge is not usable as a metric yet. Validate it on known positives first (plan step 1.9).

### 5.7 Direction vs textbook order, plain v2 (section 2)

Source: `data_output/ck12_geometry_kgx_v2/kg_eval/book_order_report.json`. 202 of 204 concepts located. Not computed for hybrids (circular).

| Relation (v2) | n | Forward rate, char [95% CI] | Forward rate, section | Expected |
|---|---|---|---|---|
| Prerequisite | 54 | 0.404 [0.27, 0.54] | 0.395 [0.24, 0.55] | forward (≈ 0.90) |
| Extension | 43 | 0.488 [0.32, 0.63] | 0.440 [0.24, 0.64] | backward (low) |
| Part-of | 216 | 0.340 [0.27, 0.40], p<0.001 | 0.297 | none |
| Application | 228 | 0.509 [0.44, 0.57] | 0.479 | none |
| Similarity | 4 | 0.500 | 0.667 | none |
| *AL-CPL gold positives* | 524 | *0.895 [0.87, 0.92]* | *0.900* | reference |
| *AL-CPL gold negatives* | 1157 | *0.325* | *0.323* | reference |

Prerequisite closure agreement 0.637 [0.55, 0.73]; Kendall τ-b (depth vs first mention) −0.022 (p=0.82); weight AUC for "points forward" 0.500.

### 5.8 Run facts

| | v2 (`run_meta.json`) | v2 hybrid (`run_meta.json`) |
|---|---|---|
| Model / where | qwen2.5:7b-instruct, Colab T4 | none, local |
| Time | 3213.6 s (53.6 min) | seconds |
| LLM calls | 3060, all succeeded | 0 |
| Pairs | 1500 scored (the cap) | all directed pairs |
| Edges | 545: Application 228, Part-of 216, Prerequisite 54, Extension 43, Similarity 4; 10 dropped to break cycles | 669: Prerequisite 518, plus 151 LLM edges (Part-of 71, Application 63, Extension 16, Similarity 1) |
| Book order used | no | yes |

### 5.9 Comparison with published results on AL-CPL geometry

| Method | Setting | F1 | AUC |
|---|---|---|---|
| RefD (Liang 2015) | supervised, in-domain | 0.504 | |
| NN | supervised, in-domain | 0.730 | |
| M1 (Liang 2018 features) | supervised, in-domain | 0.869 | |
| BERT | supervised, in-domain | 0.886 | |
| Xiao et al. 2021 | supervised, in-domain | 0.898 | 0.974 |
| ours: book_order baseline | unsupervised, one textbook | 0.71 | 0.86 |
| ours: refd_text baseline | unsupervised, one textbook | 0.40–0.42 | 0.66–0.68 |
| rule-based KG | unsupervised extraction | 0.05 | 0.51 |
| Ollama zephyr KG | unsupervised extraction | 0.03 | 0.50 |
| kg_extract v2, LLM pair votes | unsupervised extraction | 0.03 | 0.50 |
| **kg_extract v2 hybrid** (closure F1, pair-score AUC) | unsupervised, uses book order | **0.77** | **0.87** |

- Source of the published rows: Xiao et al. 2021, "Mining Precedence Relations among Lecture Videos in MOOCs via Concept Prerequisite Learning", Mathematical Problems in Engineering, Table 2 (https://onlinelibrary.wiley.com/doi/10.1155/2021/7655462). **Obtained via a search-engine summary because the publisher blocked direct access; verify against the PDF before citing.**
- Not like-for-like: published systems are trained on AL-CPL labels with Wikipedia features and classify every given pair; ours are unsupervised on one textbook, and our main set excludes pairs whose concepts are not in the KG.
- No zero-shot LLM results on AL-CPL were found. Closest: Graphusion (arXiv 2410.17600), zero-shot GPT-4 ≈ 0.75 F1 on LectureBankCD prerequisite pairs (different dataset; column mapping from a search snippet, verify).

## 6. Validity of the evaluation (what holds, what to watch)

Holds:
- Gold semantics verified against the AL-CPL README; direction strict.
- Gold labels are independent of the system and of the textbook (Wikipedia concepts, external annotators).
- Baselines on identical pairs and the AL-CPL forward-rate ceiling act as controls.
- Hybrid parameters (top-3, equal signal weights) and the concept-filter thresholds (Zipf 3.5 / 4.5) were fixed a priori, not tuned on AL-CPL.

Watch:
- Section 2 is circular for hybrid KGs (they use book order).
- Main-set pairs differ between KGs; use end_to_end for paired comparisons.
- Recall is structurally low for a sparse KG; use AUC / pair scores for comparisons.
- Concept matching is heuristic; report a high-confidence-only sensitivity run.
- Bootstrap over pairs is optimistic (pairs share concepts); switch to concept-level bootstrap.
- One book. At temperature 0 a rerun gives identical output (runs 1 and 2), so "3 runs" needs different seeds or pair orders to mean anything.
- `--hubs 10` was chosen by looking at AL-CPL candidate recall on geometry (mild leakage); fix it before running other subjects.
- The concept-precision judge is unvalidated (5.6).

## 7. Running on Colab (working recipes)

Runtime: T4 GPU; "Disconnect and delete runtime" first. Colab downloads the code from GitHub branch `ACL`, so push local changes before starting.

### 7.1 `kg_extract` run + evaluation (used for v2, 2026-10-13; about 55 min of LLM time)

```python
# 1. fresh code
%cd /content
!rm -rf /content/LearnKG /content/LearnKG-ACL /content/LearnKG.zip
!wget -q -O LearnKG.zip https://github.com/thegreatvoid/LearnKG/archive/refs/heads/ACL.zip
!unzip -q LearnKG.zip && mv LearnKG-ACL LearnKG
%cd /content/LearnKG
```
```python
# 2. packages
!pip install -q pyvis spacy wordfreq
!python -m spacy download en_core_web_sm
```
```python
# 3. Ollama (apt/debconf/systemd/"Unable to detect GPU" warnings are harmless)
!sudo apt-get update -qq && sudo apt-get install -y -qq zstd
!curl -fsSL https://ollama.com/install.sh | sh
```
```python
# 4. start server once; confirm GPU
!pkill -9 ollama || true
!nohup ollama serve > /tmp/ollama.log 2>&1 &
!sleep 5 && curl -s http://127.0.0.1:11434/
!sleep 3 && grep -i "inference compute" /tmp/ollama.log   # expect CUDA
```
```python
# 5. extractor + a different judge model; first load takes 1-3 min
!ollama pull qwen2.5:7b-instruct
!ollama pull llama3.1:8b
!time ollama run qwen2.5:7b-instruct "Say hello in one sentence."
```
```python
# 6. run (check run_meta.json: llm_ok should equal llm_calls)
!python -m kg_extract.run --data-dir ck12_geometry --model qwen2.5:7b-instruct --hubs 10 --samples 2 --out data_output/ck12_geometry_kgx_v3 2>&1 | tee /tmp/kgx.log
```
```python
# 7. evaluate (the hybrid and the LLM-free reports can also be run locally afterwards)
!python -m kg_eval.concept_quality --kg-dir data_output/ck12_geometry_kgx_v3 --judge-model llama3.1:8b --subject geometry
!python -m kg_eval.prereq_gold --kg-dir data_output/ck12_geometry_kgx_v3
```
```python
# 8. render the graph and download
from educational_pipeline.graph_builder import build_educational_graph
d = "data_output/ck12_geometry_kgx_v3"
build_educational_graph(f"{d}/concepts.csv", f"{d}/relations.csv", f"{d}/graph.html")
!zip -qr /content/kgx_v3.zip {d}
from google.colab import files; files.download("/content/kgx_v3.zip")
```

Locally: unzip into `data_output/`, then run `kg_extract.hybrid`, `prereq_gold`, `concept_quality` and (non-hybrid only) `book_order` from section 3. Open `graph.html` in a browser to view the graph.

### 7.2 `educational_pipeline` with Ollama (older, for the baseline)

Problems found in the original notebook: `yachalk` not installed made the pipeline silently run without the LLM; missing `import re` in `helpers/prompts.py` (fixed in `fcf125f`); `mv LearnKG-ACL LearnKG` into an existing folder nested the code; `--dataset deep_learning` is not on the branch.

Cells 1, 3, 4 as in 7.1, then:

```python
!pip install -q langchain pandas numpy pypdf networkx pyvis seaborn yachalk requests sentence-transformers
!ollama pull zephyr
import sys; sys.path.insert(0, "/content/LearnKG")
from helpers.prompts import educationalPrompt   # must print a dict with concepts/relations:
print(educationalPrompt("A point is a location with no dimension. A line is made of points.", model="zephyr:latest"))
!python run_pipeline.py --pipeline educational --dataset ck12_geometry --model zephyr:latest 2>&1 | tee /tmp/pipeline.log
!cd data_output && zip -qr /content/ck12_geometry_colab.zip ck12_geometry
from google.colab import files; files.download("/content/ck12_geometry_colab.zip")
```

Locally: copy only `concepts.csv` and `relations.csv` into a **new** folder `data_output/<name>/` (never into `data_output/ck12_geometry/`).

## 8. Known problems / caveats

1. **Chapter/section bugs in `educational_pipeline` (fixed in `4ff1bd5`; `ck12_geometry/` and `ck12_geometry_colab/` predate the fix and were not regenerated).**
   - `chapter_proximity` was exactly 1.0 on every edge: chapter labels are strings like `"Chapter 5: Relationships with Triangles"`, `int()` raised `ValueError`, which was caught and turned into distance 0. Fix: `chapter_number()` in `relation_extractor.py`; unknown chapter gives P = 0.5.
   - `section` was empty for all concepts and Chapter 1 concepts had no chapter: the parser only recognised a heading alone in its paragraph, but in the CK-12 text headings are followed directly by body text. Fix: `parser._split_paragraph` finds heading lines inside paragraphs (heading lines stay in the chunk text); a new chapter resets the section.
   - Chapter labels could point to the wrong chapter (e.g. `Point` in Chapter 5) because the normalizer overwrote chapter/section whenever a longer definition appeared later. Fix: first mention wins.
   - Verified on a no-LLM, no-neural run: same 130 concepts and 72 edges as before; P now 0.09–1.0, E takes 0.3/0.6/1.0, weights 0.155–1.0.
2. **Extension semantics mismatch:** `RELATION_SEMANTICS["Extension"]` in `data.py` (used by the LLM judge) says "target extends source"; the pipeline defines the opposite. Earlier judge verdicts on Extension edges are suspect. Fixing it changes judge prompts, so clear the judge cache afterwards.
3. **Concept IDs are not stable across pipeline re-runs.** Judgments keyed by `relation_id` are invalidated by a re-run. Key by (source name, target name, type) instead.
4. **`educational_pipeline` is tuned to the test book**: `concept_extractor.py` (≈ lines 81–96) hard-codes a geometry vocabulary; `relation_extractor.py` (≈ line 290 onward) has ~38 regex rules, including geometry-specific prerequisites. Test-set leakage; will not transfer.
5. `weight_source=provided` mixes LLM and neural-extractor edges in `educational_pipeline`; the neural extractor is on by default (`use_neural_model=True`) and needs `torch` (not installed locally, so local runs silently skip it).
6. `educational_pipeline` swallows LLM errors (`except Exception: pass` in `pipeline.py`). `kg_extract` counts every failure instead.
7. LLM judges tried so far are too weak: the 3B edge judge collapsed to 3s and 4s; the 8B concept judge rejects obvious concepts (5.6).
8. **The LLM pair vote has no prerequisite signal and points backward** (5.4, 5.7). The pair prompt sees the two names, their definitions and co-occurring sentences; it may need where each concept is introduced, or should only be used for relatedness and relation type.
9. **Irregular plurals are not merged** (`vertex`/`vertices`, `radius`/`radii`): `ConceptNormalizer._is_plural_match` only handles -s/-es/-ies.
10. `kg_extract` concept filters remove some real single-word terms (area, segment, similarity, leg) that only a chapter title or spaCy proposed (5.5).
11. BIGS uses MiniLM-L6 and relation_type as predicate; the paper uses other embedders (all-MiniLM-L12-v2, BAAI/bge-m3).
12. Local machine: Windows, CPU-only, ~15 GB RAM, slow downloads (the 57 MB `wordfreq` wheel took ~20 min). Use Colab (T4) for LLM work.

## 9. Plan going forward (no human annotation)

Decision so far: **continue with `kg_extract` + hybrid**, not the rule-based pipeline (caveat 4). The hybrid is the only approach that beats chance; the remaining question is whether it beats textbook order clearly and whether it transfers to other subjects.

### Step 1: evaluation fixes (in `kg_eval/`, no Colab needed)
1. ~~Make AL-CPL the main prerequisite metric~~ Done. Still to do: mark `evaluate_prerequisite_extraction.py` as deprecated (reversed-edge bug).
2. Replace LLM 1–5 ratings as the weight target with AL-CPL: weight-only AUC (reported), and rerun the ablation (`weight_ablation.py`) with AL-CPL labels as the target.
3. Fix `RELATION_SEMANTICS["Extension"]` in `data.py`; clear `judge_cache.jsonl`.
4. Concept-level (cluster) bootstrap in `data.bootstrap_ci` callers.
5. Key judgments/ratings by (source name, target name, relation type) instead of `relation_id`.
6. ~~Fix chapter proximity~~ Done (`4ff1bd5`). Regenerate `ck12_geometry/` if the baseline is still reported.
7. Meaningful replicates: vary the Ollama seed (`options.seed`) or the candidate-pair order across runs, then report mean ± SD over 3 runs.
8. High-confidence-match-only sensitivity run in `prereq_gold` (flag like `--min-confidence high`).
9. **Validate the concept-precision judge**: run it on the 89 AL-CPL concept names as known positives (they should all come back `concept`); try a larger judge on Colab (e.g. `qwen2.5:14b-instruct`) and a few labelled examples in the prompt. Report precision only once it accepts nearly all known positives.

### Step 2: pipeline changes (then rerun on Colab)
1. ~~Disable neural extractor / grounded concepts / pair scoring / stronger model / log LLM failures / record book-order use~~ Done in `kg_extract`.
2. Decide the role of the LLM pair vote (caveat 8): rework the prompt (both definitions plus the sentence where each concept is introduced), or use the LLM only for relatedness and relation type and let the hybrid decide direction.
3. Win back lost single-word terms (caveat 10): let a heading word count as a cue when it is also frequent in the body.
4. Merge irregular plurals (caveat 9).
5. Ablations: `--no-ground`, `--samples 1/2/3`, `--no-llm-concepts`, hubs 0/10/40, and parser fix vs concept filters separately.

### Step 3: multi-subject evaluation (what makes it publishable)
- AL-CPL has four subjects: data mining (120 concepts, 826 pairs, 292 positive), geometry (89 / 1681 / 524), physics (153 / 1962 / 487), precalculus (224 / 2060 / 699). Get the other three from https://github.com/harrylclc/AL-CPL-dataset.
- Pair each with a free textbook: e.g. OpenStax Physics, OpenStax Precalculus, a free data-mining textbook; keep CK-12 for geometry.
- Fix all settings (hubs, top-k, thresholds) before running the new subjects; tune on one subject, test on the others.
- `prereq_gold.py` hard-codes the geometry gold paths (`DEFAULT_ALCPL_*` in `data.py`) and the geometry synonym map; add `--pairs/--preqs` arguments and per-subject synonym maps.

### Step 4: further automatic checks
| What | Ground truth (no humans) | Metrics |
|---|---|---|
| Second gold dataset | LectureBank / LectureBankCD (NLP, CV, BIO), lecture slides as text | F1 / AUC; compare with Graphusion zero-shot GPT-4 |
| Concept extraction | AL-CPL concept lists; textbook section headings / glossary | concept recall; verbatim rate (implemented); validated precision |
| Grounding | off-the-shelf NLI model (e.g. DeBERTa-MNLI): does the evidence sentence entail the triple? + BIGS | % entailed / contradicted / neutral |
| Direction | order in a *different* textbook on the same subject (e.g. OpenStax vs CK-12) | forward rate; valid even for hybrid KGs |
| Structure | rules | cycles, duplicates, self-loops (implemented) |
| Judge calibration | run the LLM judges on AL-CPL pairs / concepts first | agreement with gold |
| Downstream | (a) learning paths vs AL-CPL prerequisite chains; (b) QA on textbook exercises with published answer keys (OpenStax), graph vs plain text vs no context | path precision, order violations; QA accuracy |

### Step 5: reporting
- Per-subject tables with concept-level bootstrap CIs; paired comparisons on end_to_end pairs; mean ± SD over 3 seeded runs.
- Always include baselines: book order, co-occurrence, co-occurrence × order, textbook RefD, random.
- Keep correctness (AL-CPL), structure, direction, concepts, weights and downstream usefulness in separate tables.
- Present the published supervised numbers (5.9) as context, labelled as supervised.

## 10. Where to start (another machine or another Claude Code instance)

1. Commit and push the v2 outputs if not done yet: `data_output/ck12_geometry_kgx_v2/` and `data_output/ck12_geometry_kgx_v2_hybrid/`.
2. Read section 5.1 for the state of results, then `kg_extract/README.md` for how the pipeline works.
3. Environment: Python 3.11 venv with `pandas numpy scipy networkx pyvis requests spacy wordfreq` and `python -m spacy download en_core_web_sm`. Check with `python kg_extract/test_kg_extract.py` (10 tests pass).
4. Reproduce the LLM-free numbers: run `prereq_gold` and `concept_quality` on `data_output/ck12_geometry_kgx_v2` and `_v2_hybrid` and compare with 5.4 / 5.5 (`kg_extract.hybrid` is deterministic).
5. Next work, in priority order: validate the concept judge (step 1.9), decide the LLM pair vote's role (step 2.2), recover lost terms (2.3), seeded replicates (1.7), then a second AL-CPL subject (step 3). LLM runs go to Colab (section 7.1).
