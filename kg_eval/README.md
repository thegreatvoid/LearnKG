# kg_eval: evaluation of the educational KG (GAPGRAPH)

Handoff document. Everything needed to continue this work without the original chat. Dates: work done 2026-10-11.

## 1. Context

- Project: `LearnKG/` builds an educational knowledge graph from a textbook (`educational_pipeline/`). Test book: CK-12 Basic Geometry (`data_input/ck12_geometry/`). Output: `data_output/ck12_geometry/{concepts,relations}.csv` (130 concepts, 90 relations).
- Edge weight = `0.52*S + 0.24*C + 0.09*P + 0.15*E` (AHP-derived), see `docs/ahp_weights.md` and `educational_pipeline/relation_extractor.py`.
  - S = Jaccard overlap of the concepts' definition words (a proxy for semantic similarity, NOT embeddings)
  - C = `min(1, cooccurrence_count/3)`
  - P = `1/(1+chapter_distance)`
  - E = 0.6 same chapter + 0.4 same section, 0.3 if neither
- Target construct for the weight (decided with the user): **educational relevance for localized graph construction**, NOT factual confidence.
- Goal of `kg_eval/`: a three-part evaluation: (A) source-grounded KG quality, (B) edge-weight validity, (C) weighting ablation. Reporting rule: keep these separate. High support does not imply completeness; structural validity does not imply factual accuracy; correlation with an LLM rating alone does not prove the weights improve the KG.

## 2. Changes made to the pipeline (all uncommitted unless pushed)

- `relations.csv` gained columns: `weight_source` (`ahp` = formula, `provided` = extractor-supplied, e.g. the neural prerequisite extractor), `cooccurrence_count`, `semantic_similarity`, `chapter_proximity`, `educational_context`. Recomputing the formula from them reproduces stored weights (max error 6e-5).
- 18 of 90 edges have `weight_source=provided` and bypass the formula; the ablation excludes them (72 remain).
- `docs/ahp_weights.md` rewritten to match the code (it previously described different factor definitions).
- `graph_builder.py` tooltip bug fixed (`int(weight)` showed 0.3 as 0).
- **Concept IDs are NOT stable across pipeline re-runs** (86 of 90 edges identical by name, IDs reshuffled). Ratings/judgments are keyed by `relation_id`, so re-running the pipeline invalidates them.

## 3. Code layout (`kg_eval/`)

| File | Role |
|---|---|
| `data.py` | loading, sentence split, Spearman/AUC/bootstrap helpers |
| `judge.py` | LLM judge via Ollama (`/api/chat`, JSON-schema output, temperature 0). Env: `OLLAMA_JUDGE_MODEL`, `OLLAMA_HOST`. Each edge is judged against the top-8 retrieved textbook sentences (MiniLM retrieval), not the whole book (whole-book prompts took >5 min per call on CPU). Cache keys include the model name. Retries 3x, skips failures. |
| `bigs.py` | BIGS (Lermanda, Ojeda, Reutter, "Evaluating Knowledge Graph Construction from Text Without Supervision", ESWC 2026). BIGS→ = mean over textbook sentences of min cosine distance to a verbalized triple; BIGS← = mean over triples of min distance to a sentence; Sym-BIGS = 1 - harmonic mean of (1-BIGS→),(1-BIGS←). Verbalization = "subject relation_type object". Embedder: cached `all-MiniLM-L6-v2`. Lower is better. |
| `source_quality.py` | Part A |
| `weight_validity.py` | Part B: `sample`, `rate`, `analyze` |
| `weight_ablation.py` | Part C |

Run from `LearnKG/` with `.venv/bin/python -m kg_eval.<module>`:

```
export OLLAMA_JUDGE_MODEL=qwen2.5:3b-instruct
python -m kg_eval.source_quality
python -m kg_eval.weight_validity sample && python -m kg_eval.weight_validity rate --reps 1 && python -m kg_eval.weight_validity analyze
python -m kg_eval.weight_ablation
```

Outputs go to `data_output/ck12_geometry/kg_eval/` (`*_report.json`, `support_judgments.csv`, `weight_sample.csv`, `judge_cache.jsonl`). The 3B-model results are archived in `kg_eval_qwen2.5-3b/`.

## 4. Methodology

**A. Source-grounded quality** (four separate reports)
1. Judged support: the LLM gets the triple, relation semantics, evidence sentence and retrieved excerpts, and returns Supported / Contradicted / Insufficient evidence / Ambiguous + quote.
2. BIGS (unsupervised source alignment, both directions).
3. Coverage: concept participation in edges, sentences reaching an edge, recall of gold prerequisite pairs (`data_input/ck12_geometry/gold_pairs.csv`).
4. Structural: duplicate edges/ids/concepts, invalid references, malformed rows, self-loops, cycles in Prerequisite and Part-of.

**B. Weight validity**: stratified sample (relation type x weight tercile, round-robin); blind LLM rating 1-5 of educational importance (rater never sees weight or support label); Spearman rho overall and per relation type with bootstrap 95% CI (types with n<10 flagged unreliable); high/mid/low weight tiers compared on support rate, concepts covered, gold-prerequisite hits.

**C. Ablation**: edges/concepts frozen, only the weight function varies. Variants: uniform, S/C/P/E-only, full minus each component (remaining AHP weights renormalized), full AHP, full tuned on dev (grid over simplex, step 0.05, maximizing Spearman with ratings). Metrics: Spearman vs rating, AUC for rating>=4, paired bootstrap of (full rho - variant rho). Split: chapters 1-6 dev, 7-12 held-out (single book; edges with no chapter unassigned).

## 5. Results so far (judge = qwen2.5:3b-instruct, a weak judge)

**A** (judge-independent items are reliable)
- Structural: all clean (0 duplicates, invalid refs, malformed, self-loops, cycles).
- Coverage: 61/130 concepts (47%) appear in any edge; 0/24 gold prerequisite pairs recovered with direction (2/24 ignoring direction).
- BIGS: BIGS→ 0.466, BIGS← 0.283, Sym-BIGS 0.388 (cosine distance; triples fairly grounded, textbook only partly covered).
- Judged support (88 of 90 edges; R0040 and R0042 failed with truncated JSON): Supported 60%, Insufficient 26%, Contradicted 14%. Not hand-verified.

**B**: overall rho 0.05 (95% CI -0.16 to 0.26, n=90); Prerequisite n=34 rho -0.03; Similarity n=46 rho -0.09; Part-of/Application/Extension n<=6 (unreliable). Weight tiers indistinguishable on rating, support. **The judge rated 58/90 edges as 4, 29 as 3, only 3 below, so there is almost no variance; B tells us nothing yet.**

**C**: stored weights recomputed exactly (rho=1.0). No variant correlates with ratings (held-out rho -0.12 to +0.19, all within noise); full formula beats no ablation (CIs include 0); dev tuning picked E=1.0 alone (dev rho 0.03, noise).

## 6. Known problems / caveats

1. **`chapter_proximity` is exactly 1.0 on every edge** (chapter labels inconsistent; 19/130 concepts have none). P cannot be learned or ablated until chapter assignment is fixed upstream.
2. Judge too weak (3B). Needs a stronger judge (larger Ollama model or Anthropic API) and ideally human educator ratings; LLM-only ratings are circular.
3. Single-book chapter split is weak: 45 dev / 27 held-out edges (rho SE ~0.19 at n=30), edges are clustered (shared concepts, chunks, sentences) so the edge-level bootstrap is too optimistic, tuning 231 grid points on 45 edges overfits, same author/pipeline/judge on both sides so it is not a cross-textbook test, and constant components (P) cannot be tested. Needs 3-4+ books with leave-one-book-out.
4. Retrieval-based judge context (top-8 sentences) may miss relevant evidence.
5. BIGS here uses MiniLM-L6 and relation_type as the predicate; the paper's experiments use other embedders (e.g. all-MiniLM-L12-v2, BAAI/bge-m3).
6. Extractor-weighted (neural) edges are excluded from the ablation.
7. Machine constraints seen: CPU-only, ~15 GB RAM, disk tight. Ollama calls ~30-45 s each with the 3B model.

## 7. Suggested next steps

1. Stronger judge: pull `qwen2.5:7b-instruct` (needs ~5 GB free disk) or add an Anthropic-API judge backend; re-run B and C.
2. Fix chapter assignment so P varies; consider embedding-based S.
3. Add more textbooks; per-book split; human ratings on a stratified sample.
4. Downstream usefulness test (e.g. localized subgraph for a tutoring/QA task).
5. Assessment given to the user: not conference-paper-ready; plausible as a workshop draft, or a main-track paper after multi-book data, human ratings, a working positive/negative weight result and a downstream task.
