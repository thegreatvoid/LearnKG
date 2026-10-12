# kg_extract: grounded, domain-agnostic extraction (concepts -> candidate pairs -> LLM pair scores)

Replaces the geometry-tuned rule/regex extraction of `educational_pipeline/` (kept as the baseline). Rationale and diagnosis: see `kg_eval/README.md` sections 8-9. Output schema is identical (`concepts.csv`, `relations.csv`) plus `pair_scores.csv`, so `kg_eval` runs unchanged.

## Stages (`python -m kg_extract.run --data-dir ck12_geometry --model qwen2.5:7b-instruct`)

1. `concepts.py`: candidates from section headings, definition patterns ("X is a", "A X is/has ...", "called X"), spaCy noun chunks, and (unless `--no-llm-concepts`) an LLM that names terms *introduced* in each chunk (JSON schema, temperature 0). **Grounding filter**: a term is kept only if it occurs verbatim (plural-tolerant) in the book; `--no-ground` is an ablation switch. Salience (heading/definition/LLM cue + log frequency in the body text) picks the top-K; ties go to the more domain-specific term. No domain vocabulary. Every candidate, its cues and why it was dropped are written to `concept_candidates.csv`.
   - Noise filters (added 2026-10-12): chapter titles are not candidates; a section heading "X of/about/using Y" gives Y ("Properties of Parallel Lines" -> Parallel Lines), coordinated headings share the head noun ("Isosceles and Equilateral Triangles"), and a heading term must also occur in the body. Noun chunks are parsed line by line, skip arithmetic expressions ("pi times radius"), drop point labels ("angle ABC" -> angle) and strip verbs spaCy mis-tags as nouns ("the hinge theorem states that" -> hinge theorem). Definition patterns no longer truncate "called remote interior angles" to "remote" and skip "X is the mnemonic/used to". A candidate found only as a noun chunk must pass a domain-specificity test using general-English word frequency (`wordfreq`, optional): a single word must be rare (Zipf < 3.5, e.g. "hypotenuse" yes, "sides" no), and a phrase whose words are all common (Zipf >= 4.5, e.g. "specific examples") is dropped. Thresholds were fixed a priori, not tuned on gold. Without `wordfreq` installed, single words found only as noun chunks are dropped and phrases are not checked.
2. `pairs.py`: candidate pairs from sentence co-occurrence, "A's definition mentions B", same-chunk co-occurrence, optional embedding neighbours, and `--hubs H` (the H most foundational concepts are paired with every concept; foundational = most sentences + definition mentions). Book order is **not** used.
3. `score.py`: for each candidate, 2+ LLM samples (A/B order swapped on odd samples to cancel position bias) return `{relation, source, confidence}`; a sample votes `confidence` for (relation, direction); the score is vote mass / successful samples. Written to `pair_scores.csv` (one row per direction, `score_<Relation>` columns).
4. `consistency.py`: one label per pair (highest score >= `--threshold`), Prerequisite and Part-of forced acyclic by dropping the lowest-score edge of each cycle.
5. `backend.py`: Ollama JSON-schema chat with retries; failures are counted (`run_meta.json` -> `counters`, `backend_counters`), never swallowed.

`run_meta.json` records `uses_book_order: false`. If a future variant uses book order, do not report `kg_eval.book_order` on that book.

## Evaluate

```
python -m kg_eval.concept_quality --kg-dir data_output/<run>      # verbatim rate, AL-CPL concept recall, candidate recall
python -m kg_eval.concept_quality --kg-dir data_output/<run> --judge-model llama3.1:8b --subject geometry   # + LLM-judged concept precision
python -m kg_eval.prereq_gold     --kg-dir data_output/<run>      # now also scores kg_pairscore (AUC over all pairs)
python -m kg_eval.source_quality --kg-dir ...                      # BIGS / structure / judge (as before)
```
Inspect the parser/structure/chunker output (they are in-memory only, never saved otherwise): add `--dump-intermediate` to `kg_extract.run`; it writes `<out>/intermediate/{parsed_blocks,structured_blocks,chunks}.csv`. It works with `--candidates-only --no-llm-concepts`, so no LLM is needed.

Offline unit tests: `python kg_extract/test_kg_extract.py`.

## Measurements so far (CK-12 geometry; no LLM concept stage, no pair scoring yet)

| Setting | Concepts | verbatim in text | AL-CPL concept recall (any / high-conf.) | gold positive pairs the generator considered |
|---|---|---|---|---|
| old rule-based pipeline | 130 | 1.00 | 0.73 / 0.69 | n/a (edges only) |
| kg_extract rules+spaCy, top-k 150 | 116 | 1.00 | 0.57 / 0.53 | 31% (706 pairs) |
| top-k 250, per-concept 8 | 197 | 0.995 | 0.72 / 0.69 | 24% (1197 pairs) |
| top-k 250, per-concept 8, hubs 10 | ~197 | 0.995 | 0.72 / 0.69 | 51% (2453 pairs) |
| top-k 250, per-concept 8, hubs 40 | ~197 | 0.995 | 0.72 / 0.69 | 73% (7299 pairs) |
| top-k 400 | 346 | 0.994 | 0.81 / 0.78 | 21-33% |
| top-k 250 + noise filters (2026-10-12; per-concept 8, no hubs) | 203 (baseline same settings: 194) | 1.00 | 0.74 / 0.73 (baseline 0.71 / 0.69) | 54% (baseline 36%) |

- Without any geometry vocabulary, concept recall matches the old tuned pipeline (0.72) at top-k 250: the generality cost is small once enough candidates are kept.
- **The pair generator is the bottleneck.** Gold prerequisites are often conceptual links (e.g. Point -> Line) with no shared sentence, so co-occurrence candidates reach only 21-37% of gold positives. Embedding neighbours did not help. Pairing foundational "hub" concepts with everything raises the upper bound to 51% (hubs 10) / 73% (hubs 40) at 2.5k / 7.3k pairs. `--hubs` was chosen by looking at AL-CPL recall on geometry: fix it before running other subjects (leakage otherwise).
- Cost: with `qwen2.5:3b-instruct` on CPU, one pair-scoring call takes ~6 s (short prompts), so 2453 pairs x 2 samples is roughly 8 h locally and should be ~1-2 h on a Colab T4 with a 7B model.
- Rule/spaCy noise ("times", "states", "sum", "half", "sides", "remote", "properties", chapter titles) is removed by the noise filters above, with concept recall up rather than down. Remaining noise without the LLM stage: some generic phrases ("logical argument", "common endpoint"), adjectives tagged as nouns ("triangular", "Isosceles"), "SOH CAH TOA", irregular plurals not merged with their singular ("radii", "vertices"). Precision is not measured yet: run `concept_quality --judge-model` with a model different from the extractor's.
- Smoke test (8 pairs, 3B model): the whole path ran with 16/16 successful LLM calls and a valid `pair_scores.csv`; the result itself is not meaningful.

## Next steps

1. Run on Colab T4 with `qwen2.5:7b-instruct`: `python -m kg_extract.run --data-dir ck12_geometry --model qwen2.5:7b-instruct --hubs 10 --samples 2` (see `kg_eval/README.md` section 7 for the Colab recipe; add `pip install spacy wordfreq && python -m spacy download en_core_web_sm`), 3 runs, then the three `kg_eval` commands above.
2. Compare `kg_pairscore` AUC with `book_order` (0.86) and the old KG (0.51). Success = clearly above 0.5 without book order.
3. Ablations: `--no-ground`, `--samples 1/2/3`, `--no-llm-concepts`, hubs 0/10/40.
4. Other AL-CPL subjects (needs `--pairs/--preqs` and subject synonym maps in `kg_eval/prereq_gold.py`, `kg_eval/data.py`).

## Hybrid KG construction (`kg_extract/hybrid.py`) and first result

`python -m kg_extract.hybrid --run data_output/ck12_geometry_kgx_run1 --out data_output/ck12_geometry_kgx_hybrid` rebuilds the KG from a finished run with no LLM calls and no gold labels: every directed concept pair is scored as `forward-in-book-order x mean percentile rank of (order gap, co-occurrence, RefD, LLM relatedness)`; each concept keeps its top-3 *related* predecessors as Prerequisite edges (acyclic); the LLM's Part-of / Application / Extension / Similarity edges are added for other pairs. **It uses book order** (`uses_book_order: true`): do not report `kg_eval.book_order` direction checks on this KG's own book.

Result on CK-12 geometry (run 1 input; AL-CPL, matched and located pairs, n=1061):

| Predictor | P | R | F1 | ROC-AUC [95% CI] |
|---|---|---|---|---|
| kg_prereq (Prerequisite edges) | 0.90 | 0.18 | 0.30 | 0.585 |
| kg_closure (transitive) | 0.86 | 0.65 | **0.74** | 0.806 |
| kg_pairscore (hybrid score, all pairs) | 0.87 | 0.13 | 0.23 | **0.872 [0.85, 0.89]** |
| book_order baseline | 0.56 | 0.95 | 0.70 | 0.856 [0.83, 0.88] |
| previous best KG (LLM pair vote) | | | 0.03 | 0.505 |

Caveats: the AUC gain over book order is small and the confidence intervals overlap; top-k=3 and equal signal weights were fixed a priori (not tuned on gold) but this is one book; concept noise from spaCy chunks ("states", "times", "sum") is still present and shows up as hubs in the graph; the graph is dense (562 Prerequisite edges for 209 concepts).
