# Second-domain evaluation protocol (pre-registration)

Purpose: test whether the weighting results from CK-12 geometry (`kg_eval/README.md` section 5.11) hold on an
independent subject, without adapting the method to that subject. Written 2026-10-15, before any second-domain data
was obtained.

## 1. What is frozen

Everything listed in `kg_eval/freeze_manifest.py`: the parser, structure detector, chunker, concept extractor,
normaliser, definition finder, relation extractor (factors and `WEIGHTING_SCHEMES`), pipeline, dataset builder, the
evaluation scripts and their settings (NDCG@5/10, 20 tie-breaks, 2000 bootstrap resamples over queries, 5-fold CV with
grid step 0.1, 20000 sign flips, MiniLM-L6 embedder). Procedure:

1. Review and commit the code.
2. `python -m kg_eval.freeze_manifest --write`, then commit `kg_eval/frozen_manifest.json`.
3. Only now download the second-domain textbook and AL-CPL files.
4. Before every second-domain run and before reporting: `python -m kg_eval.freeze_manifest --check` must print OK.

The three schemes compared are exactly `ahp` (expert baseline), `cooc_only` and `cooc_struct_a0.8`. `alpha = 0.8` came
from CK-12 cross-validation; on the second domain it is a fixed, pre-specified value, not re-tuned. The learned-weights
row (D) is re-estimated by cross-validation inside the new subject only, and is reported as such.

## 2. Primary comparisons (pre-specified)

1. `scheme cooc_only` vs `scheme ahp`, NDCG@10 (paired, same queries).
2. `scheme cooc_struct_a0.8` vs `scheme ahp`, NDCG@10.
3. `book order gate x C` vs `book order (gap)`, NDCG@10: does the weight add anything beyond textbook order?

Report mean paired difference, bootstrap 95% CI over queries and the sign-flip p-value for each, plus NDCG@5 as
secondary. Three primary tests: if a significance claim is made, use Holm correction. Everything else in the output
(single factors, ablations, BIGS) is exploratory.

## 3. Data

- Subject: AL-CPL **physics** (153 concepts, 1962 labelled pairs, 487 positive) or **precalculus** (224 / 2060 / 699),
  from https://github.com/harrylclc/AL-CPL-dataset. Pick one before downloading the textbook; use the other later as a
  third, untouched test.
- Textbook: an OpenStax book for the subject (e.g. *College Physics 2e* or *Precalculus 2e*, CC BY), converted to
  plain text with chapter headings as `Chapter N: Title` and section headings as `N.M Title` on their own lines (the
  format the parser recognises). Record the conversion command and the book version; do not edit the text by hand
  after looking at results.
- Concept matching: `match_gold_concept` uses generic matching plus `GEOMETRY_SYNONYM_MAP`, which was written for
  geometry while looking at geometry gold names. No synonym map may be written for the new subject; report how many
  gold concepts are matched with the generic rules only.

## 4. Commands

```
python -m kg_eval.freeze_manifest --check
python -c "from educational_pipeline import run_educational_pipeline as r; r(data_dir='<subject>', output_base_dir='./data_output/second_domain', use_llm=False, embedding_similarity=True, output_html='./data_output/second_domain/<subject>.html')"
python -m kg_eval.prereq_gold     --kg-dir data_output/second_domain/<subject> --source data_input/<subject>/<book>.txt --pairs data_input/<subject>/<subject>.pairs --preqs data_input/<subject>/<subject>.preqs
python -m kg_eval.weight_ranking  --kg-dir data_output/second_domain/<subject> --source data_input/<subject>/<book>.txt --pairs data_input/<subject>/<subject>.pairs --preqs data_input/<subject>/<subject>.preqs
python -m kg_eval.direction_check --kg-dir data_output/second_domain/<subject> --source data_input/<subject>/<book>.txt --pairs data_input/<subject>/<subject>.pairs --preqs data_input/<subject>/<subject>.preqs
```

## 5. Known limits that the second domain will NOT fix

- `educational_pipeline/concept_extractor.py` contains a hard-coded geometry vocabulary (`DOMAIN_TERMS`) and
  `relation_extractor.py` contains geometry regex rules. On a new subject they contribute nothing, so the KG there is
  built by the generic parts only. That is the honest test of the generic parts, but it is not the same system that
  produced the geometry KG. The weight-ranking test is less affected: it scores concept pairs, not edges.
- AL-CPL labels prerequisites, not "educational relevance".
- Symmetric factors cannot decide direction; direction is checked separately (`direction_check`).

## 6. Full evaluation framework on the second domain (added 2026-10-15)

`kg_eval.framework` (report: `data_output/eval_framework/REPORT.md`) evaluates concepts, all five relation types,
weights, grounding and the concept-level gap proxy. To repeat it on the second domain without changing the method:

1. The framework modules are listed in `FROZEN_FILES` in `kg_eval/freeze_manifest.py`, so writing the manifest also
   freezes the evaluation itself.
2. Point the framework at the new subject: register the new KG folders in `common.KGS` and pass the new textbook and
   AL-CPL files (`common.gold(pairs, preqs)`, `DEFAULT_SOURCE`). This is configuration, not a method change.
3. Prerequisite: AL-CPL labels for the subject give [GT] results with the same protocol (common covered set,
   unmatched pairs as coverage loss, query-level bootstrap). Do not check direction against the same book's order
   for a KG built with book order; if a second textbook of the subject is available, use its order instead.
4. Part-of / Application / Similarity / Extension: run `annotation_kit build` on the new KGs and annotate with the same
   guidelines (`kg_eval/framework/ANNOTATION_GUIDELINES.md`), two annotators, kappa, adjudication. Without these
   labels report only the [AUTO] diagnostics; do not report precision/recall.
5. Report every table separately per textbook and per relation type. No pooled "overall" score across subjects.
