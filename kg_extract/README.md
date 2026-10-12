# kg_extract: grounded, domain-agnostic extraction (concepts -> candidate pairs -> LLM pair scores)

Replaces the geometry-tuned rule/regex extraction of `educational_pipeline/` (kept as the baseline). Rationale and diagnosis: see `kg_eval/README.md` sections 8-9. Output schema is identical (`concepts.csv`, `relations.csv`) plus `pair_scores.csv`, so `kg_eval` runs unchanged.

## Stages (`python -m kg_extract.run --data-dir ck12_geometry --model qwen2.5:7b-instruct`)

1. `concepts.py`: candidates from headings, definition patterns ("X is a", "called X"), spaCy noun chunks, and (unless `--no-llm-concepts`) an LLM that names terms *introduced* in each chunk (JSON schema, temperature 0). **Grounding filter**: a term is kept only if it occurs verbatim (plural-tolerant) in the book; `--no-ground` is an ablation switch. Salience (heading/definition/LLM cue + log frequency) picks the top-K. No domain vocabulary.
2. `pairs.py`: candidate pairs from sentence co-occurrence, "A's definition mentions B", same-chunk co-occurrence, optional embedding neighbours, and `--hubs H` (the H most foundational concepts are paired with every concept; foundational = most sentences + definition mentions). Book order is **not** used.
3. `score.py`: for each candidate, 2+ LLM samples (A/B order swapped on odd samples to cancel position bias) return `{relation, source, confidence}`; a sample votes `confidence` for (relation, direction); the score is vote mass / successful samples. Written to `pair_scores.csv` (one row per direction, `score_<Relation>` columns).
4. `consistency.py`: one label per pair (highest score >= `--threshold`), Prerequisite and Part-of forced acyclic by dropping the lowest-score edge of each cycle.
5. `backend.py`: Ollama JSON-schema chat with retries; failures are counted (`run_meta.json` -> `counters`, `backend_counters`), never swallowed.

`run_meta.json` records `uses_book_order: false`. If a future variant uses book order, do not report `kg_eval.book_order` on that book.

## Evaluate

```
python -m kg_eval.concept_quality --kg-dir data_output/<run>      # verbatim rate, AL-CPL concept recall, candidate recall
python -m kg_eval.prereq_gold     --kg-dir data_output/<run>      # now also scores kg_pairscore (AUC over all pairs)
python -m kg_eval.source_quality --kg-dir ...                      # BIGS / structure / judge (as before)
```
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

- Without any geometry vocabulary, concept recall matches the old tuned pipeline (0.72) at top-k 250: the generality cost is small once enough candidates are kept.
- **The pair generator is the bottleneck.** Gold prerequisites are often conceptual links (e.g. Point -> Line) with no shared sentence, so co-occurrence candidates reach only 21-37% of gold positives. Embedding neighbours did not help. Pairing foundational "hub" concepts with everything raises the upper bound to 51% (hubs 10) / 73% (hubs 40) at 2.5k / 7.3k pairs. `--hubs` was chosen by looking at AL-CPL recall on geometry: fix it before running other subjects (leakage otherwise).
- Cost: with `qwen2.5:3b-instruct` on CPU, one pair-scoring call takes ~6 s (short prompts), so 2453 pairs x 2 samples is roughly 8 h locally and should be ~1-2 h on a Colab T4 with a 7B model.
- Rule/spaCy candidates still produce noise ("states", "sides"); the LLM concept stage plus salience is expected to remove it; not yet measured.
- Smoke test (8 pairs, 3B model): the whole path ran with 16/16 successful LLM calls and a valid `pair_scores.csv`; the result itself is not meaningful.

## Next steps

1. Run on Colab T4 with `qwen2.5:7b-instruct`: `python -m kg_extract.run --data-dir ck12_geometry --model qwen2.5:7b-instruct --hubs 10 --samples 2` (see `kg_eval/README.md` section 7 for the Colab recipe; add `pip install spacy && python -m spacy download en_core_web_sm`), 3 runs, then the three `kg_eval` commands above.
2. Compare `kg_pairscore` AUC with `book_order` (0.86) and the old KG (0.51). Success = clearly above 0.5 without book order.
3. Ablations: `--no-ground`, `--samples 1/2/3`, `--no-llm-concepts`, hubs 0/10/40.
4. Other AL-CPL subjects (needs `--pairs/--preqs` and subject synonym maps in `kg_eval/prereq_gold.py`, `kg_eval/data.py`).
