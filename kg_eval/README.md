# kg_eval: evaluation of the educational KG (GAPGRAPH)

Handoff document: everything needed to continue this work on another machine without the original chats. Work done 2026-10-11 (two sessions). Section 9 is the plan going forward; section 10 is the "where to start" checklist.

## 1. Context

- Project: `LearnKG/` builds an educational knowledge graph from a textbook (`educational_pipeline/`, entry point `run_pipeline.py --pipeline educational`). Test book: CK-12 Basic Geometry (`data_input/ck12_geometry/ck12_basic_geometry_concepts.txt`, 21 KB, 59 numbered sections).
- Two KGs of the same book exist and are evaluated side by side:

| Folder | How it was made | Concepts / relations / Prerequisite edges |
|---|---|---|
| `data_output/ck12_geometry/` | `educational_pipeline` locally, **no LLM** (rule-based + neural prerequisite extractor) | 130 / 90 / 34 |
| `data_output/ck12_geometry_colab/` | Same `educational_pipeline`, run in Google Colab **with Ollama `zephyr:latest`** (+ neural extractor), see section 7 | 209 / 364 / 118 |

- **The "Colab notebook" is not a separate extractor.** It downloads this repo and runs `run_pipeline.py --pipeline educational`, i.e. the same parser → structure detector → chunker → concept/relation extraction → `dataset_builder` chain, with the LLM switched on. Earlier Colab runs most likely never used the LLM (section 7).
- Edge weight = `0.52*S + 0.24*C + 0.09*P + 0.15*E` (AHP-derived), see `docs/ahp_weights.md` and `educational_pipeline/relation_extractor.py`.
  - S = Jaccard overlap of the concepts' definition words (a proxy for semantic similarity, NOT embeddings)
  - C = `min(1, cooccurrence_count/3)`
  - P = `1/(1+chapter_distance)`, 0.5 if either chapter is unknown (was constant 1.0 in the KGs evaluated below, see caveats)
  - E = 0.6 same chapter + 0.4 same section, 0.3 if neither (the +0.4 never fired in the KGs evaluated below, see caveats)
  - Edges with `weight_source=provided` (LLM- or neural-extractor-supplied weight) bypass the formula.
- Target construct for the weight (decided with the user): **educational relevance for localized graph construction**, NOT factual confidence.
- Relation ontology (5 types) as defined by the pipeline (`relation_extractor.py` header, `helpers/prompts.py` `educationalPrompt`):
  - Prerequisite: A → B, A must be understood before B
  - Part-of: A is a component of B
  - Application: A is applied/used in B
  - **Extension: A builds upon / extends B (so A comes later than B)**
  - Similarity: undirected in meaning
- Constraint decided by the user: **the evaluation plan must not involve human annotation** (section 9).

## 2. Changes made to the code (state as of 2026-10-11)

Earlier session (committed in `650fc8e` / `7078785` unless noted):
- `relations.csv` gained columns: `weight_source` (`ahp` = formula, `provided` = extractor-supplied), `cooccurrence_count`, `semantic_similarity`, `chapter_proximity`, `educational_context`. Recomputing the formula reproduces stored weights (max error 6e-5).
- `docs/ahp_weights.md` rewritten to match the code; `graph_builder.py` tooltip bug fixed (`int(weight)` showed 0.3 as 0).

Second session (**uncommitted** at time of writing; commit before switching machines):
- `kg_eval/prereq_gold.py` (new): section 1 evaluation vs AL-CPL.
- `kg_eval/book_order.py` (new): section 2 evaluation vs textbook order.
- `kg_eval/data.py`: `load_kg` now accepts other CSV layouts (name-based `source`/`target`, `relationship` column, missing IDs/weights); new helpers `average_precision`, `prf`, `load_alcpl`, `term_pattern`, `first_position`, `section_starts`, `section_index`, `concept_terms`.
- `helpers/prompts.py`: added missing `import re`. Without it, `educationalPrompt` raised `NameError` on any LLM response that was not clean JSON, and the pipeline's bare `except: pass` silently dropped the LLM output. **Must be pushed to the ACL branch on GitHub**, because Colab downloads the code from there (the Colab recipe patches it on the fly until then).
- `data_output/ck12_geometry_colab/` (new): the Ollama KG + its `kg_eval/` reports.
- `data_output/ck12_geometry/kg_eval/`: new `prereq_gold_*` and `book_order_*` outputs.
- A `--from-csv` option was added to `run_pipeline.py` during the session, then reverted outside the session; it is **not** present. `kg_eval` no longer depends on it. (It built the Pyvis graph directly from existing CSVs; easy to re-add if wanted.)
- `docs/index.html` shows as modified; not changed by the evaluation work.

## 3. Code layout (`kg_eval/`)

| File | Role | Needs LLM? |
|---|---|---|
| `data.py` | loading (+ layout adapter), sentence split, text-position helpers, AL-CPL loader, Spearman/AUC/AP/PRF/bootstrap helpers | no |
| `prereq_gold.py` | **Section 1**: prerequisite correctness vs AL-CPL gold, with text baselines | no |
| `book_order.py` | **Section 2**: edge direction vs textbook teaching order | no |
| `judge.py` | LLM judge via Ollama (`/api/chat`, JSON-schema output, temperature 0). Env: `OLLAMA_JUDGE_MODEL`, `OLLAMA_HOST`. Each edge judged against top-8 retrieved textbook sentences (MiniLM). Cache keys include model name. Retries 3x. | yes |
| `bigs.py` | BIGS (Lermanda, Ojeda, Reutter, ESWC 2026). BIGS→ = mean over textbook sentences of min cosine distance to a verbalized triple; BIGS← = mean over triples of min distance to a sentence; Sym-BIGS = 1 − harmonic mean of (1−BIGS→),(1−BIGS←). Embedder `all-MiniLM-L6-v2`. Lower is better. | no |
| `source_quality.py` | Part A (judged support, BIGS, coverage, structure) | partly |
| `weight_validity.py` | Part B: `sample`, `rate`, `analyze` | yes |
| `weight_ablation.py` | Part C | uses Part B ratings |

### Running

From `LearnKG/` (Windows: `python`, Linux/macOS venv: `.venv/bin/python`).

LLM-free (seconds each). `--kg-dir` = any folder with `concepts.csv` + `relations.csv`; `--out` defaults to `<kg-dir>/kg_eval`; `--source` overrides the textbook `.txt`:

```
python -m kg_eval.prereq_gold --kg-dir data_output/ck12_geometry
python -m kg_eval.book_order  --kg-dir data_output/ck12_geometry
python -m kg_eval.prereq_gold --kg-dir data_output/ck12_geometry_colab
python -m kg_eval.book_order  --kg-dir data_output/ck12_geometry_colab
```

LLM-judge parts (slow on CPU, ~30-45 s per call with a 3B model):

```
export OLLAMA_JUDGE_MODEL=qwen2.5:3b-instruct
python -m kg_eval.source_quality
python -m kg_eval.weight_validity sample && python -m kg_eval.weight_validity rate --reps 1 && python -m kg_eval.weight_validity analyze
python -m kg_eval.weight_ablation
```

Outputs: `<kg-dir>/kg_eval/` (`prereq_gold_report.json`, `prereq_gold_pairs.csv`, `book_order_report.json`, `book_order_edges.csv`, `*_report.json`, `support_judgments.csv`, `weight_sample.csv`, `judge_cache.jsonl`). The 3B-judge results are archived in `data_output/ck12_geometry/kg_eval_qwen2.5-3b/`.

## 4. Methodology

### Section 1: prerequisite correctness vs AL-CPL (`prereq_gold.py`)

- Gold: **AL-CPL** geometry (Liang et al., AAAI 2018; https://github.com/harrylclc/AL-CPL-dataset), files `data_input/ck12_geometry/geometry.pairs` (1681 labelled pairs) and `geometry.preqs` (524 positives). A line `A,B` means **B is a prerequisite of A** (dataset README: "predict whether the 2nd concept is a prerequisite of the 1st"). It is recovered by a KG edge `B → A`.
- Gold concept names (Wikipedia titles) are matched to KG concepts with `match_gold_concept` from `evaluate_prerequisite_extraction.py` (synonym map → exact → plural → token → fuzzy). Low-confidence matches are listed in the report.
- **Direction is strict.** A KG edge pointing the wrong way counts as wrong. `evaluate_prerequisite_extraction.py` counts reversed edges as true positives (`extracted_pred = directed_pred or reversed_pred`), so its numbers are inflated; do not report them.
- Predictors (all scored on the same pairs; score > 0 = predicted positive):
  - `kg_prereq` Prerequisite edge B → A, score = weight **[main result]**
  - `kg_closure` B reaches A via Prerequisite edges, score = 1/path length
  - `kg_any_relation` any relation type B → A
  - `kg_undirected` Prerequisite either direction (diagnostic only)
  - `book_order` B first mentioned before A in the book
  - `cooccurrence` sentence co-occurrence count (undirected)
  - `cooc_x_order` co-occurrence, only when B precedes A
  - `refd_text` RefD (Liang et al. 2015) adapted to textbook sentences: `|S_A∩S_B|/|S_A| − |S_A∩S_B|/|S_B|`
- Evaluation sets: **main** = pairs where both concepts matched to distinct KG concepts and both located in the text (all predictors comparable); **end_to_end** = all 1681 pairs, unmatched = "no edge" (KG predictors only).
- Metrics: precision, recall, F1, MCC, ROC-AUC, PR-AUC (average precision); bootstrap 95% CI over pairs for F1 and AUC; "weight-only" AUC among pairs that have a KG edge.

### Section 2: direction vs textbook order (`book_order.py`)

- Position of a concept = first whole-word, case-insensitive, plural-tolerant mention of its name or aliases in the textbook (avoids the broken chapter labels). Also at section granularity (numbered sections like `1.2`; same section = tie).
- Expected direction: **Prerequisite → forward** (source mentioned first); **Extension → backward** (pipeline defines "source extends target"); other types have no expected direction.
- Metrics: forward rate per relation type with bootstrap CI and two-sided binomial test vs 0.5; Prerequisite closure agreement (all u ⇝ v pairs); Kendall τ-b of prerequisite depth vs position; weight AUC for "edge points forward"; **reference**: forward rate of AL-CPL gold positives (90%) and negatives (32%) in this book, which is the realistic ceiling.
- **Circularity warning:** if the system itself uses book order (e.g. flips Prerequisite edges to match it), this check becomes trivially satisfied for that book. From then on, report it only against a *different* textbook (see plan, step 4).

### Parts A–C (LLM-judge based, first session)

- **A. Source-grounded quality**: judged support (Supported / Contradicted / Insufficient evidence / Ambiguous + quote), BIGS, coverage, structural checks (duplicates, invalid refs, malformed rows, self-loops, cycles in Prerequisite and Part-of).
- **B. Weight validity**: stratified sample (relation type × weight tercile); blind LLM rating 1–5 of educational importance; Spearman ρ overall and per type with bootstrap CI; weight tiers compared.
- **C. Ablation**: edges frozen, only the weight function varies (uniform, single components, leave-one-out, full AHP, tuned on dev). Spearman vs rating, AUC for rating ≥ 4, paired bootstrap. Split: chapters 1–6 dev, 7–12 held-out.
- Status: B and C are being **retired as primary evidence** (LLM ratings are circular and collapsed to almost all 4s); they are replaced by AL-CPL-based weight evaluation in the plan.

## 5. Results (CK-12 Basic Geometry)

### 5.1 Side by side (sections 1 and 2)

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
3. Ollama's Prerequisite edges lean backward (34% forward at section level, vs 90% for true prerequisites): direction is the main defect.
4. A third of Ollama's Prerequisite edges use concept names that do not occur in the book (e.g. "Triangle Congruence using AAS" → "Triangle Congruence using ASA"): hallucinated / over-specific concepts.
5. Weights carry no signal in either KG.
6. The trivial "textbook order" baseline beats both KGs by a wide margin and is the bar to clear.
7. Rule-based backward edges are mostly part→whole mislabelled as Prerequisite (e.g. `Chord → Circle`, `Angle Bisector → Angle`, `Perpendicular Bisector → Point`).
8. `weight_source=provided` mixes Ollama and neural-extractor edges, so the Ollama run cannot yet be attributed to Ollama alone.

### 5.2 Parts A–C (rule-based KG, judge = qwen2.5:3b-instruct, weak)

- Structural: all clean (0 duplicates, invalid refs, malformed, self-loops, cycles).
- Coverage: 61/130 concepts (47%) appear in any edge; 0/24 hand-written gold pairs (`data_input/ck12_geometry/gold_pairs.csv`) recovered with direction (2/24 ignoring direction).
- BIGS: BIGS→ 0.466, BIGS← 0.283, Sym-BIGS 0.388.
- Judged support (88 of 90 edges): Supported 60%, Insufficient 26%, Contradicted 14%. Not validated.
- B: overall ρ 0.05 (95% CI −0.16 to 0.26, n=90). Judge rated 58/90 edges as 4 and 29 as 3: no variance, uninformative.
- C: no weight variant correlates with ratings (held-out ρ −0.12 to +0.19, all noise).

### 5.3 Comparison with published results on AL-CPL geometry

| Method | Setting | F1 | AUC |
|---|---|---|---|
| RefD (Liang 2015) | supervised, in-domain | 0.504 | |
| NN | supervised, in-domain | 0.730 | |
| M1 (Liang 2018 features) | supervised, in-domain | 0.869 | |
| BERT | supervised, in-domain | 0.886 | |
| Xiao et al. 2021 | supervised, in-domain | 0.898 | 0.974 |
| ours: book_order baseline | unsupervised, one textbook | 0.71 | 0.86 |
| ours: refd_text baseline | unsupervised, one textbook | 0.42 | 0.68 |
| rule-based KG | unsupervised extraction | 0.05 | 0.51 |
| Ollama zephyr KG | unsupervised extraction | 0.03 | 0.50 |

- Source of the published rows: Xiao et al. 2021, "Mining Precedence Relations among Lecture Videos in MOOCs via Concept Prerequisite Learning", Mathematical Problems in Engineering, Table 2 (https://onlinelibrary.wiley.com/doi/10.1155/2021/7655462). **Obtained via a search-engine summary because the publisher blocked direct access; verify against the PDF before citing.**
- These are not like-for-like: published systems are trained on AL-CPL labels with Wikipedia features and classify every given pair; our KG only proposes a few edges, which caps recall. The pair-scoring mode in the plan (step 2) makes the setups comparable.
- No zero-shot LLM results on AL-CPL were found. Closest: Graphusion (arXiv 2410.17600), zero-shot GPT-4 ≈ 0.75 F1 on LectureBankCD prerequisite pairs (different dataset; column mapping from a search snippet, verify). Realistic target for a strong LLM scoring pairs: 0.7–0.8 F1.

## 6. Validity of the evaluation (what holds, what to watch)

Holds:
- Gold semantics verified against the AL-CPL README; direction strict.
- Gold labels are independent of the system and of the textbook (Wikipedia concepts, external annotators).
- Baselines on identical pairs and the AL-CPL forward-rate ceiling act as controls.

Watch:
- Section 2 becomes circular once the system uses book order (see section 4).
- Recall is structurally low for a sparse KG; use AUC / pair-scoring for comparisons.
- Concept matching is heuristic; report a high-confidence-only sensitivity run.
- Bootstrap over pairs is optimistic (pairs share concepts); switch to concept-level bootstrap.
- Single LLM run, single book; LLM output varies between runs.

## 7. Running the Ollama pipeline in Colab (working recipe)

Problems found in the previous notebook:
- `yachalk` was not installed → `from helpers.prompts import educationalPrompt` failed → the pipeline silently ran **without** the LLM.
- Missing `import re` in `helpers/prompts.py` (fixed locally; patched in cell 2 until pushed).
- `mv LearnKG-ACL LearnKG` into an existing `/content/LearnKG` nested the code one level deeper → "can't open file run_pipeline.py".
- `--dataset deep_learning` is not on the GitHub branch; evaluation needs `ck12_geometry`.
- The first Ollama request loads the 4 GB model onto the GPU and takes 1–3 min; it is not stuck.

Runtime: T4 GPU; "Disconnect and delete runtime" first. Cells, run in order:

```python
# 1. fresh code
%cd /content
!rm -rf /content/LearnKG /content/LearnKG-ACL /content/LearnKG.zip
!wget -q -O LearnKG.zip https://github.com/thegreatvoid/LearnKG/archive/refs/heads/ACL.zip
!unzip -q LearnKG.zip && mv LearnKG-ACL LearnKG
%cd /content/LearnKG
!ls run_pipeline.py data_input/ck12_geometry
```
```python
# 2. deps + import-re patch
!pip install -q langchain pandas numpy pypdf networkx pyvis seaborn yachalk requests sentence-transformers
!grep -q "^import re" helpers/prompts.py || sed -i '1i import re' helpers/prompts.py
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
!sleep 3 && grep -i "inference compute" /tmp/ollama.log   # expect library=CUDA
```
```python
# 5-6. model + warm-up (wait, don't interrupt)
!ollama pull zephyr
!time ollama run zephyr "Say hello in one sentence."
```
```python
# 7. confirm LLM extraction works (must print a dict with concepts/relations)
import sys; sys.path.insert(0, "/content/LearnKG")
from helpers.prompts import educationalPrompt
print(educationalPrompt("A point is a location with no dimension. A line is made of points. "
                        "A line segment is part of a line with two endpoints.", model="zephyr:latest"))
```
```python
# 8. run (10-30 min)
!python run_pipeline.py --pipeline educational --dataset ck12_geometry --model zephyr:latest 2>&1 | tee /tmp/pipeline.log
```
```python
# 9-10. check and download
import pandas as pd
rel = pd.read_csv("data_output/ck12_geometry/relations.csv"); print(len(rel)); print(rel.relation_type.value_counts())
!cd data_output && zip -qr /content/ck12_geometry_colab.zip ck12_geometry
from google.colab import files; files.download("/content/ck12_geometry_colab.zip")
```

Locally: copy only `concepts.csv` and `relations.csv` into a **new** folder `data_output/<name>/` (never into `data_output/ck12_geometry/`), then run the section 3 commands with `--kg-dir data_output/<name>`.

## 8. Known problems / caveats

1. **Chapter/section bugs in the KGs evaluated here (fixed in code 2026-10-12; the stored KGs in `data_output/` predate the fix and must be regenerated).**
   - `chapter_proximity` was exactly 1.0 on every edge. Cause: chapter labels are strings like `"Chapter 5: Relationships with Triangles"`; `int()` on them raised `ValueError`, which was caught and turned into distance 0. Fix: `chapter_number()` in `relation_extractor.py` parses the number; unknown chapter gives P = 0.5.
   - `section` was empty for all concepts, and Chapter 1 concepts had no chapter (19/130). Cause: the parser only recognised a heading when it was alone in its paragraph, but in the CK-12 text headings are followed directly by body text. Fix: `parser._split_paragraph` finds heading lines inside paragraphs (heading lines stay in the chunk text, so extraction is unchanged); a new chapter resets the section. As a result E's "same section" +0.4 never fired before.
   - Chapter labels could point to the wrong chapter (e.g. `Point` in Chapter 5) because the normalizer overwrote a concept's chapter/section whenever a longer definition appeared later. Fix: chapter/section are now those of the first mention.
   - Verified on a no-LLM, no-neural run: same 130 concepts and 72 edges as before (differences are only singular/plural canonical names and the direction of 4 undirected Similarity edges); P now ranges 0.09-1.0, E takes 0.3/0.6/1.0, weights 0.155-1.0.
2. **Extension semantics mismatch:** `RELATION_SEMANTICS["Extension"]` in `data.py` (used by the LLM judge) says "target extends source"; the pipeline defines the opposite. Earlier judge verdicts on Extension edges are suspect. Fixing it changes judge prompts, so clear the judge cache afterwards.
3. **Concept IDs are not stable across pipeline re-runs** (86 of 90 edges identical by name, IDs reshuffled). Judgments keyed by `relation_id` are invalidated by a re-run. Key by (source name, target name, type) instead.
4. **The rule-based pipeline is tuned to the test book**: `concept_extractor.py` (≈ lines 81–96) hard-codes a geometry vocabulary; `relation_extractor.py` (≈ line 290 onward) has ~38 regex rules, including geometry-specific prerequisites (e.g. Pythagorean theorem → Right Triangle). This is test-set leakage and will not transfer to other subjects.
5. `weight_source=provided` mixes LLM and neural-extractor edges; the neural extractor is on by default (`use_neural_model=True` in `pipeline.py`).
6. The pipeline swallows LLM errors (`except Exception: pass` in `pipeline.py`); a broken LLM path silently produces rule-based output. Add a log line / counter for LLM successes.
7. LLM judge too weak (3B) and its 1–5 ratings collapsed; retrieval context (top-8 sentences) may miss evidence.
8. Single book; edge-level bootstrap is optimistic; single LLM run.
9. BIGS uses MiniLM-L6 and relation_type as predicate; the paper uses other embedders (all-MiniLM-L12-v2, BAAI/bge-m3).
10. Local machine constraints seen: CPU-only, ~15 GB RAM, tight disk; use Colab (T4) for LLM work.

## 9. Plan going forward (no human annotation)

Decision: **continue with the LLM (Ollama) route, not the rule-based pipeline**, because the rule-based extractor is hand-tuned to the test book (caveat 4) and cannot be evaluated fairly or transferred. Keep its reusable parts (structure-aware chunking, normalizer, grounded definitions); drop the hard-coded geometry vocabulary and regex relations. The Ollama run was handicapped (zephyr 7B is an old model, mixed with neural edges, no grounding, free-form generation).

Key method change: from "LLM generates free-form triples" to **(1) grounded concept extraction** (keep only terms found in the text, or map to the nearest one that is) **+ (2) pair scoring** (for candidate pairs of concepts that appear near each other, ask "is A a prerequisite of B?" with the textbook sentences as evidence, and keep the probability). This gives a score for every pair (AUC becomes meaningful), makes results comparable to the literature, and allows thresholds tuned on one subject to be applied to others.

### Step 1: fix the current evaluation (all in `kg_eval/`, no Colab needed)
1. Make AL-CPL (`prereq_gold`) the main prerequisite metric; mark `evaluate_prerequisite_extraction.py` as deprecated (reversed-edge bug).
2. Replace LLM 1–5 ratings as the weight target with AL-CPL: weight-only AUC, and rerun the ablation (`weight_ablation.py`) with AL-CPL labels as the target.
3. Fix `RELATION_SEMANTICS["Extension"]` in `data.py`; clear `judge_cache.jsonl`.
4. Concept-level (cluster) bootstrap in `data.bootstrap_ci` callers.
5. Key judgments/ratings by (source name, target name, relation type) instead of `relation_id`.
6. ~~Compute P from first-mention positions~~ Chapter labels are fixed (caveat 1); first-mention position remains an option for finer-grained P. Regenerate both KGs and rerun all reports.
7. Support multiple runs per configuration (mean ± SD).
8. High-confidence-match-only sensitivity run in `prereq_gold` (flag like `--min-confidence high`).

### Step 2: pipeline changes (then rerun on Colab)
1. Add a flag to disable the neural extractor (`use_neural_model=False`) and get an Ollama-only result.
2. Grounded concept extraction: drop/map concepts not found in the text.
3. Pair-scoring mode: candidate pairs = concepts co-occurring within a window/section; LLM returns P(prereq) with evidence; write scores to `relations.csv` (or a separate `pair_scores.csv`).
4. Stronger model on the Colab T4 (e.g. `qwen2.5:7b-instruct` or `llama3.1:8b`), temperature 0, 3 runs.
5. Log LLM success/failure counts instead of silently passing.
6. If book order is used to fix direction, record that, and stop reporting section 2 on the same book.

### Step 3: multi-subject evaluation (what makes it publishable)
- AL-CPL has four subjects: data mining (120 concepts, 826 pairs, 292 positive), geometry (89 / 1681 / 524), physics (153 / 1962 / 487), precalculus (224 / 2060 / 699). Get the other three from https://github.com/harrylclc/AL-CPL-dataset.
- Pair each with a free textbook: e.g. OpenStax Physics, OpenStax Precalculus, a free data-mining textbook; keep CK-12 for geometry.
- Tune thresholds/weights on one subject, test on the others (leave-one-subject-out).
- `prereq_gold.py` currently hard-codes the geometry gold paths (`DEFAULT_ALCPL_*` in `data.py`) and the geometry synonym map; add `--pairs/--preqs` arguments and per-subject synonym maps.

### Step 4: further automatic checks
| What | Ground truth (no humans) | Metrics |
|---|---|---|
| Second gold dataset | LectureBank / LectureBankCD (NLP, CV, BIO), lecture slides as text | F1 / AUC; compare with Graphusion zero-shot GPT-4 |
| Concept extraction | AL-CPL concept lists; textbook section headings / glossary | concept recall; % of concepts found verbatim in text (hallucination rate) |
| Grounding | off-the-shelf NLI model (e.g. DeBERTa-MNLI): does the evidence sentence entail the triple? + BIGS | % entailed / contradicted / neutral |
| Direction | order in a *different* textbook on the same subject (e.g. OpenStax vs CK-12) | forward rate; independent even if the system uses its own book's order |
| Structure | rules | cycles, duplicates, self-loops (implemented) |
| Judge calibration | run the LLM judge on AL-CPL pairs first | agreement with gold; if good, trust the judge on edges outside AL-CPL |
| Downstream | (a) learning paths vs AL-CPL prerequisite chains; (b) QA on textbook exercises with published answer keys (OpenStax), graph vs plain text vs no context | path precision, order violations; QA accuracy |

### Step 5: reporting
- Per-subject tables with concept-level bootstrap CIs; paired bootstrap between systems; mean ± SD over 3 LLM runs.
- Always include baselines: book order, co-occurrence, co-occurrence × order, textbook RefD, random.
- Keep correctness (AL-CPL), structure, direction, weights and downstream usefulness in separate tables.
- Present the published supervised numbers (5.3) as context, labelled as supervised; our setting is unsupervised extraction.

## 10. Where to start on a new machine

1. Commit and push the uncommitted work listed in section 2 (including `helpers/prompts.py` and `data_output/ck12_geometry_colab/`).
2. Clone, `pip install -r requirements.txt` (plus `scipy`, `networkx`, `pandas`), then run the four LLM-free commands in section 3 and check the numbers against section 5.1.
3. Do plan step 1 (evaluation fixes), then step 2 (pipeline changes) and rerun on Colab with section 7.
