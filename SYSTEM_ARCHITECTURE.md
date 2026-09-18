# LearnKG — System Architecture Reference

This document is the definitive technical reference for the LearnKG codebase at
`/home/dino/finyr/LearnKG`. It is derived directly from reading the source files
(paths and line-level details cited throughout). It cross-references, and does
not contradict, the existing `PROJECT_DOCUMENTATION.md` and `RUNNING.md`.

---

## 1. High-Level Overview

LearnKG turns educational source documents (plain-text or PDF textbook chapters,
e.g. `data_input/foundations_of_machine_learning/`) into a **structured,
ontology-constrained knowledge graph** of concepts and pedagogical relations,
persisted as CSV files (`concepts.csv`, `relations.csv`) plus derived graph
statistics (`concept_stats.csv`, `graph_summary.json`) and an interactive
Pyvis/vis.js HTML visualization (`docs/index.html`).

A FastAPI backend (`kg_chatbot/`) loads that same CSV-based knowledge graph into
memory and answers free-text questions by matching the question to the most
relevant concept node, building a small localized subgraph of prerequisites and
related concepts around it (via BFS + weighted ranking), detecting likely
"knowledge gaps" (prerequisite concepts the user probably hasn't seen yet), and
generating an answer — either a deterministic template built from grounded
source text, or (if a local Ollama LLM is configured and reachable) a more
natural LLM-phrased answer constrained to the same graph context.

A React 19 + Vite + TypeScript single-page app (`webapp/`) is the user-facing
client: it presents a chat panel, a ReactFlow graph visualization of the
localized subgraph returned by the backend, an insights panel (knowledge gaps,
prerequisites, related concepts), and a node-details panel. The whole system
therefore has three independently runnable stages: (1) an offline ETL/graph
construction pipeline, (2) an API server over the resulting graph, and (3) a
frontend that talks to that API.

There is also a **legacy pipeline** (`helpers/`, `ollama/`, the `--pipeline
legacy` branch of `run_pipeline.py`) predating the "educational" pipeline. It
uses LangChain document loaders/splitters and an LLM (via a local Ollama
server) to extract arbitrary directed `(source, target, relationship, weight)`
triples with no fixed ontology — this is the original "extract_graph.ipynb"
style approach, kept for backwards compatibility and reference.

---

## 2. Repository Layout

```
LearnKG/
├── educational_pipeline/   # Core ETL: parses documents → concepts.csv / relations.csv (10-step pipeline)
├── kg_chatbot/              # FastAPI backend serving Q&A over the generated graph
├── helpers/                 # Legacy LangChain+Ollama extraction helpers (df_helpers.py, prompts.py)
├── ollama/                  # Thin REST client for a local Ollama server (client.py)
├── webapp/                  # React 19 + Vite + TS frontend (chat + graph visualization)
├── data_input/               # Source documents per dataset (e.g. cureus/, foundations_of_machine_learning/)
├── data_output/              # Per-dataset generated CSVs (concepts.csv, relations.csv, concept_stats.csv, graph_summary.json, legacy graph.csv/chunks.csv)
├── docs/                     # Generated Pyvis/vis.js HTML visualizations (index.html, graph.html) — also served as GitHub Pages docs
├── old_notebooks/            # Legacy Jupyter notebooks predating the educational_pipeline package
├── local_ollama/             # A vendored ollama binary/tarball + log — a local, non-package Ollama install
├── assets/                   # README/diagram images (drawio, banner, sample PDFs)
├── run_pipeline.py           # CLI entry point: dispatches to educational or legacy pipeline
├── run_directed.py           # Standalone script: rebuilds docs/index.html from already-generated CSVs (no re-extraction)
├── run_educational.bat / run_directed.bat / powershell.bat   # Windows convenience wrappers
├── test_educational_pipeline.py  # Verification script: runs the educational pipeline end-to-end, checks CSV schema/ontology
├── extract_graph.ipynb, ner.ipynb  # Standalone notebooks (older exploratory work, outside old_notebooks/)
├── Dockerfile                # Poetry-based image that launches JupyterLab (not the FastAPI server)
├── pyproject.toml / poetry.lock   # Poetry dependency spec (legacy-pipeline-oriented; missing fastapi/uvicorn/pydantic — see §9)
├── environment.yml           # Conda equivalent of pyproject.toml (also missing fastapi/uvicorn — see §9)
├── RUNNING.md                 # Step-by-step run instructions (condensed in §8 below)
└── PROJECT_DOCUMENTATION.md   # Earlier, shorter architecture write-up of the educational_pipeline only
```

---

## 3. `educational_pipeline/` — Core ETL / Graph Construction Pipeline

This package implements a 10-step pipeline, orchestrated by
`pipeline.py::run_educational_pipeline`. Each step is its own module.

### 3.1 `parser.py` — Step 1: Document Parsing

- `ParsedBlock` dataclass: `text, page, source_file, chapter, section, is_heading, metadata`.
- `_detect_heading(line)`: regex-based heading detector. Recognizes:
  - `Chapter <num>[: title]` → `("chapter", "Chapter N: Title")`
  - `Section <num>` or `N.N Title` → `("section", ...)`
  - A fixed set of common top-level header words (introduction, background,
    overview, methods, results, discussion, conclusion, summary, review,
    abstract, references, exercises, problems, case study).
- `parse_text_file(filepath)`: splits on blank lines into paragraphs; estimates
  page numbers at ~2500 chars/page unless an explicit `--- Page N ---` or
  `[Page N]` marker is found (which is stripped from the text); tracks running
  `current_chapter`/`current_section` state as headings are encountered.
- `parse_pdf_file(filepath)`: uses `pypdf.PdfReader`, iterates real PDF pages
  (so page numbers are exact, not estimated), splits each page's extracted
  text on blank lines, applies the same heading detection. Falls back to
  `parse_text_file` if `pypdf` is not importable.
- `parse_document(filepath)`: dispatches on file extension (`.pdf` vs. else).

### 3.2 `structure_detector.py` — Step 2: Educational Structure Detection

- `EDUCATIONAL_TYPES`: `{Chapter, Section, Definition, Explanation, Example,
  Exercise, Theorem, Proof, Algorithm, Summary}`.
- `StructuredBlock` dataclass: `text, block_type, page, source_file, chapter, section`.
- `RULES`: ordered list of `(block_type, regex)` pairs matched against the
  first line (then, as a fallback, the first 120 chars) of a block's text:
  - `Definition`: `^(?:Definition|Def\.?)...`
  - `Theorem`: `^(?:Theorem|Lemma|Proposition|Corollary)...`
  - `Proof`: `^(?:Proof|Proof of ...)...`
  - `Algorithm`: `^(?:Algorithm|Procedure|Pseudocode)...`
  - `Example`: `^(?:Example|Worked Example)...`
  - `Exercise`: `^(?:Exercise|Problem|Question|Practice)...`
  - `Summary`: `^(?:Summary|Key Takeaways|Chapter Summary|Review Summary)...`
- `detect_block_type(block)`: if `block.is_heading`, classify as `Chapter` or
  `Section`; else run the `RULES`; default fallback is `Explanation`.
- `detect_educational_structures(blocks)`: applies `detect_block_type` to every
  `ParsedBlock`, propagating `current_chapter`/`current_section` context
  forward, producing a flat `List[StructuredBlock]`.

### 3.3 `chunker.py` — Step 3: Structure-Aware Chunking

- `EducationalChunk` dataclass: `chunk_id (uuid4 hex), text, block_type, chapter, section, page, source_file`.
- `create_structure_aware_chunks(blocks, target_size=1500, max_size=2200)`:
  - `standalone_types = {Definition, Theorem, Proof, Algorithm, Example, Exercise, Summary}`
    are never merged with surrounding text — each becomes its own chunk (split
    further along paragraph boundaries at `target_size` increments only if it
    exceeds `max_size`).
  - `Chapter`/`Section` blocks flush the current buffer and update context
    without becoming chunks themselves (they carry no body text on their own).
  - Regular `Explanation` blocks accumulate into a buffer, flushed whenever the
    buffer would exceed `target_size` chars or the chapter/section changes.
  - This preserves pedagogical unit boundaries instead of naive fixed-size
    windowing (contrast with the legacy pipeline's
    `RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)`).

### 3.4 `concept_extractor.py` — Step 4: Concept Extraction

- `STOPWORDS`: generic English stopwords plus textbook noise words (figure,
  table, section, chapter, page, study, analysis, example, exercise, results,
  author(s), approach, method).
- `TYPE_KEYWORDS`: keyword lists mapping to 5 concept types — `Algorithm`,
  `Model`, `Formula`, `Theory`, `Component` — used by `infer_concept_type(name)`
  (substring match against the lowercased concept name; defaults to
  `Component`).
- `DOMAIN_TERMS`: a fixed whitelist of ~28 ML/calculus terms (Machine Learning,
  Gradient Descent, Backpropagation, Adam, RMSProp, Sigmoid Function, etc.)
  always checked for presence in each chunk.
- `extract_candidate_concepts_from_text(text)`: combines 5 deterministic
  signal sources into a candidate set:
  1. Capitalized 2-4 word phrases (`[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}`).
  2. Acronyms (`[A-Z]{2,6}` or the literals `RMSProp`/`Adam`), excluding common
     words like AND/THE/FOR/NOT.
  3. Quoted/italicized short phrases.
  4. Text following "defined as / known as / termed / called / referred to as".
  5. Any `DOMAIN_TERMS` present via regex search.
- `extract_concepts_for_chunk(chunk, llm_concepts=None)`: merges LLM-supplied
  concepts (if any, keyed case-insensitively) with the deterministic
  candidates above, producing `{concept_name, aliases, concept_type,
  definition, evidence}` dicts (LLM concepts take priority; deterministic
  candidates fill gaps).

### 3.5 `normalizer.py` — Step 5: Concept Normalization & Entity Linking

- `NormalizedConcept` dataclass: `concept_id (C0001, ...), concept_name,
  aliases: Set[str], concept_type, definition, chapter, section, page,
  chunk_id, evidence`.
- `ConceptNormalizer` maintains `concepts_by_id` and a `lookup` dict
  (lowercased name/alias → concept_id), assigning sequential `C%04d` IDs.
- `clean_name(name)`: strips trailing punctuation and leading articles
  (the/a/an).
- Matching cascade in `find_match(name)`, tried in order:
  1. Exact lowercase lookup hit.
  2. `_is_plural_match`: simple `s`/`es`/`-ies→-y` suffix rules.
  3. `_is_acronym_match`: a ≤5-char uppercase string matches the initials of
     an existing multi-word term (or vice versa).
  4. `_is_fuzzy_match(threshold=0.87)`: `difflib.SequenceMatcher` ratio, only
     applied when both strings are ≥6 chars and length difference ≤6 — catches
     near-duplicate phrasing like "Neural Network" vs. "Neural Networks Model".
- `register_concept(...)`: looks up an existing match; if found, merges
  aliases and (if the new definition is longer/non-empty) updates
  definition/evidence/chapter/section/page/chunk_id, and upgrades
  `concept_type` away from the default `Component`. Otherwise creates a new
  `NormalizedConcept` with a fresh ID.
- `get_all_concepts()`: returns concepts sorted by ID.

### 3.6 `definition_extractor.py` — Step 6: Definition Extraction

- `DEFINITION_PATTERNS`: 4 regexes for "X is defined as Y", "X refers to Y",
  "X is a/an Y that/which/used to/designed to/responsible for Z", and
  "Definition: X is Y" (these patterns are defined but the primary logic below
  does its own sentence-level search rather than iterating this list).
- `extract_grounded_definition(concept_name, text)`: for each sentence in the
  chunk (split on `.?!` boundaries):
  1. Search for `"<concept> is/are/refers to/is defined as [a/an/the]? <predicate>"`
     and build `"{concept} is {predicate}"` if the predicate is >15 chars.
  2. Fallback: check if the text starts with `"Concept: definition"`.
  3. Fallback: return the first sentence (30–250 chars) that merely mentions
     the concept, as grounding evidence — ensuring every definition/evidence
     pair is a **verbatim source sentence**, never a hallucinated one.

### 3.7 `relation_extractor.py` — Steps 7, 8, 9: Relations, Ontology, Weighting

- `VALID_ONTOLOGY_TYPES = {Prerequisite, Part-of, Application, Extension, Similarity}`
  — the controlled 5-type educational relation ontology (Prerequisite and
  Part-of/Application/Extension are directed A→B; Similarity is symmetric).
- `ONTOLOGY_PATTERNS`: dict mapping each of the 5 types to a list of trigger
  keywords/phrases (e.g. Prerequisite: "prerequisite", "required for",
  "depends on", "foundation for", "must understand", ...; Part-of: "part of",
  "component of", "consists of", "subset of", ...; Application: "applied to",
  "used for", "trained by", "optimizes", ...; Extension: "extends", "builds
  upon", "variant of", "generalization of", ...; Similarity: "similar to",
  "analogous to", "resembles", "equivalent to", ...).
- `classify_relation(raw_predicate)`: exact-match against ontology names first,
  then keyword substring match across `ONTOLOGY_PATTERNS`, else defaults to
  `Application`.
- **AHP-derived edge weight formula** (documented as coming from the project
  report, Consistency Ratio CR = 0.022):
  ```
  AHP_FACTOR_WEIGHTS = {
      semantic_similarity: 0.52,
      cooccurrence:        0.24,
      chapter_proximity:   0.09,
      educational_context: 0.15,
  }
  weight = 0.52*semantic_similarity + 0.24*cooccurrence
         + 0.09*chapter_proximity + 0.15*educational_context   # clipped to [0,1]
  ```
  - `semantic_similarity(c1, c2)`: Jaccard overlap of word sets from
    `definition` (falling back to `concept_name`) — a dependency-free proxy
    for embedding cosine similarity.
  - `chapter_proximity(c1, c2)`: `1 / (1 + |chapter1 - chapter2|)` (numeric
    chapter distance; 0 if non-numeric).
  - `educational_context_score`: +0.6 if same chapter, +0.4 if same section,
    minimum 0.3 otherwise.
  - `cooccurrence`: `min(1, times_pair_seen_together / 3)`, tracked per
    `(source_id, target_id)` pair in `RelationManager._pair_cooccurrence`.
- `ExtractedRelation` dataclass: `relation_id (R0001,...), source_id, target_id,
  relation_type, weight, page, chunk_id, evidence`.
- `RelationManager`:
  - `add_relation(...)`: resolves source/target names to concept IDs via the
    normalizer (skips if either is unmatched or they're the same concept),
    classifies the relation type, computes/accepts a weight, dedups on
    `(source_id, target_id, relation_type)` (bumping weight to the max on a
    repeat rather than creating a duplicate edge).
  - `extract_relations_from_sentences(sentences, page, chunk_id)`: two-pass
    rule-based extractor per sentence (skipping sentences <20 chars):
    1. **~28 hand-written high-confidence "pedagogical_rules"** — regex →
       `(source_name, target_name, relation_type)` triples specific to the ML
       textbook domain (e.g. `"guided by calculus"` → Calculus→Machine
       Learning Prerequisite; `"mini-batch gradient descent"` → Mini-Batch
       Gradient Descent→Gradient Descent Extension; `"sigmoid function"` →
       Sigmoid Function→Logistic Regression Part-of). These are checked first
       and unconditionally added if the pattern matches.
    2. **General co-occurrence + keyword rule**: finds all registered concepts
       (by canonical name or any alias) mentioned in the sentence; if ≥2
       distinct concepts co-occur, and any `ONTOLOGY_PATTERNS` keyword appears
       in the sentence, adds a relation between every ordered pair of found
       concepts for that ontology type.

### 3.8 `dataset_builder.py` — Step 10: Dataset Construction

- `CONCEPTS_COLUMNS = [concept_id, concept_name, aliases, concept_type,
  definition, chapter, section, page, chunk_id, evidence]`
- `RELATIONS_COLUMNS = [relation_id, source_id, target_id, relation_type,
  weight, page, chunk_id, evidence]`
- `build_and_save_dataset(normalizer, relation_manager, output_dir)`: builds
  the two `pandas.DataFrame`s (aliases joined with `", "`, newlines stripped
  from definition/evidence) and writes `concepts.csv` / `relations.csv` via
  `to_csv(..., index=False, encoding="utf-8")`. Returns both file paths.

### 3.9 `graph_builder.py` — Downstream: Pyvis Visualization

- `RELATION_COLORS`: fixed hex color per relation type (Prerequisite=crimson
  `#d90429`, Part-of=sapphire `#0077b6`, Application=teal `#2a9d8f`,
  Extension=amber `#f4a261`, Similarity=amethyst `#7209b7`).
- `hls_palette(n)`: generates `n` perceptually distinct colors via
  `colorsys.hls_to_rgb`, shuffled.
- `build_educational_graph(concepts_csv, relations_csv, output_html=...,
  show_edge_labels=False, show_edge_tooltips=True, show_edge_weights=True,
  min_edge_weight=0.3)`:
  1. Loads both CSVs as strings, builds a `networkx.DiGraph`.
  2. Adds one node per concept with an HTML tooltip (`title`) containing name,
     type, definition, aliases, chapter/page.
  3. Adds one edge per relation row, **dropping edges with weight <
     `min_edge_weight` (0.3)** to reduce clutter; builds a tooltip with
     relation type, weight, and the evidence quote; for `Similarity` edges
     also adds the reverse edge if absent (making Similarity effectively
     bidirectional in the rendered graph).
  4. **Community detection**: `nx.community.girvan_newman` on the undirected
     projection, taking the *second* partition level (`next(gen)` called
     twice) — each community gets a distinct HLS color, stored as node
     `group`/`color`.
  5. **Node sizing**: `nx.pagerank(G, weight="weight", max_iter=200)`,
     min-max normalized into pixel size range `[12, 57]`; falls back to raw
     degree-based sizing if PageRank fails.
  6. Pins edge `width`/`value` to a constant 1 (edge thickness is NOT scaled
     by weight in the final render — weight is only visible via label/tooltip)
     — deliberately, per an in-code comment, to avoid pyvis's automatic
     `from_nx()` width-from-weight behavior.
  7. Renders via `pyvis.network.Network(directed=True, cdn_resources="remote",
     height="900px")`, custom `forceAtlas2Based` physics options, writes HTML
     to `output_html` (default `./docs/index.html`).

### 3.10 `graph_stats.py` — Graph Statistics ("Knowledge Graph Repository" cache)

- `_load_graph`: builds a plain (unstyled) `DiGraph` from the full relation
  set — no `min_edge_weight` filtering (unlike `graph_builder.py`), and
  collapses duplicate `(src,tgt)` edges by keeping the max weight.
- `compute_graph_statistics(concepts_csv, relations_csv, output_dir)`
  precomputes, once offline (so query-time lookups are O(1) instead of
  recomputing centrality per request):
  - **Per concept** → `concept_stats.csv`: `concept_id, concept_name,
    pagerank, in_degree, out_degree, degree_centrality,
    betweenness_centrality, clustering_coefficient, community` — sorted
    descending by pagerank.
  - **Graph-level** → `graph_summary.json`: `nodes, edges, density,
    avg_degree, avg_edge_weight, avg_clustering_coefficient,
    weakly_connected_components, communities, top_5_by_pagerank`.
  - Uses the same Girvan-Newman (2nd partition level) community algorithm as
    `graph_builder.py`. PageRank falls back to normalized in-degree
    centrality if `nx.pagerank` fails (e.g. scipy missing); betweenness
    centrality falls back to all-zeros on failure.

### 3.11 `pipeline.py` — Orchestrator: `run_educational_pipeline`

Signature:
```python
run_educational_pipeline(
    data_dir="cureus", input_base_dir="./data_input", output_base_dir="./data_output",
    output_html="./docs/index.html", model="zephyr:latest", use_llm=True,
    show_edge_labels=False, show_edge_tooltips=True,
) -> (concepts_csv_path, relations_csv_path, nx.DiGraph)
```
Executes, in order:
1. **Parse**: gathers `*.pdf`/`*.txt` under `data_input/<data_dir>/` (or, if
   empty, files matching `<data_dir>*` directly under `data_input/`), parses
   each via `parse_document`.
2. **Structure detect** on all blocks combined.
3. **Chunk** via `create_structure_aware_chunks`.
4–6. **Concept extraction/normalization/definitions** — for each chunk, if
   `use_llm` (and `helpers.prompts.educationalPrompt` importable), calls the
   LLM (`educationalPrompt(chunk.text, model=model)`) to get `{concepts,
   relations}`; extracted concepts are merged with `extract_concepts_for_chunk`
   deterministic candidates; if a concept has no definition yet,
   `extract_grounded_definition` is used to ground one from the chunk text;
   every concept is registered into the shared `ConceptNormalizer`.
   LLM-extracted relations are stashed per-chunk (`llm_results_by_chunk`) for
   step 7.
7–9. **Relations**:
   - (A) If a precomputed legacy `graph.csv` exists in the output dir (`|`
     -separated, columns `node_1/node_2/edge` or `source/target/relationship`),
     its rows are ingested and classified into the 5-type ontology too
     (bridging the legacy pipeline's output into the educational one).
   - (B) LLM relations from step 4-6 are added via `RelationManager.add_relation`,
     with the LLM's 1-10 weight rescaled to `[0,1]` via `(w-1)/9` so it's
     comparable to the AHP-derived weight.
   - (C) Sentence-level co-occurrence + pedagogical-rule extraction
     (`extract_relations_from_sentences`) runs over every chunk using the
     **full, corpus-wide concept registry** (so relations can span across
     chunks/chapters, not just within-chunk).
10. **Dataset construction** → `concepts.csv`, `relations.csv`.
11. **Graph statistics** → `concept_stats.csv`, `graph_summary.json`.
12. **Downstream graph** → `build_educational_graph` → `docs/index.html`.

`use_llm=True` is the default but LLM calls are best-effort: any exception
during `educationalPrompt` is swallowed (`except Exception: pass`) and the
pipeline continues deterministically for that chunk.

### 3.12 `run_pipeline.py` (repo root) — CLI Entry Point

```
python run_pipeline.py --pipeline {educational|legacy} --dataset <name> \
    [--model zephyr:latest] [--no-llm] [--show-edge-labels]
```
- `--pipeline educational` (default) calls `run_educational_pipeline` directly.
- `--pipeline legacy` runs the **original LangChain-based pipeline**, inline
  in this same file:
  1. `DirectoryLoader(f"./data_input/{data_dir}").load()`.
  2. `RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)`.
  3. `documents2Dataframe(pages)` → chunk_id-tagged DataFrame.
  4. If `regenerate=True` or no `graph.csv` cached: `df2Graph(df, model)` (LLM
     extraction per chunk) → `graph2Df(...)` → save `graph.csv` (`|`-sep) and
     `chunks.csv`. Otherwise loads the cached `graph.csv`, remapping the old
     `node_1/node_2/edge` schema to `source/target/relationship` if needed.
  5. **Contextual proximity** (`contextual_proximity(df)`): melts
     source/target into long form per `chunk_id`, self-joins on `chunk_id` to
     get every co-occurring node pair, counts occurrences, keeps only pairs
     that co-occur **more than once**, assigns `relationship="contextual
     proximity"`, `weight = min(count, 3)` — a low-confidence, low-weight
     "these appeared together" edge type layered under the LLM-derived edges.
  6. **Merge**: concatenates LLM-directed edges + proximity edges, groups by
     `(source, target)`, sums weights, joins `chunk_id`/`description` strings.
  7. Builds an `nx.DiGraph`.
  8. **Community detection**: `nx.community.girvan_newman` on the undirected
     projection, 2nd partition level (same pattern as `graph_builder.py`).
  9. **Node styling**: `colors2Community` (via seaborn `hls` palette) for
     community color; **PageRank** (`nx.pagerank(G, weight="weight")`, falling
     back to in-degree centrality on non-convergence) scaled `size =
     max(10, int(pagerank*1000))`.
  10. Renders via Pyvis with `curvedCW` smoothing and arrowheads
      (`directed=True`), writes to `output_html`.

### 3.13 `run_directed.py` (repo root) — Standalone Rebuild Script

A dependency-light, no-re-extraction script meant to be run directly
(`python run_directed.py`) to just re-render `docs/index.html` from whatever
CSVs already exist, without needing LangChain/seaborn/scipy:
- Auto-installs `pandas`/`numpy`/`networkx`/`pyvis` via `pip` if missing.
- **If `data_output/cureus/{concepts,relations}.csv` exist**: delegates
  directly to `educational_pipeline.graph_builder.build_educational_graph`
  and exits — this is the primary path for the current dataset.
- **Else, fallback**: loads the legacy `data_output/cureus/graph.csv`
  directly, remaps old schema if needed, recomputes contextual proximity
  edges (same algorithm as `run_pipeline.py`'s legacy branch), merges, builds
  the `DiGraph`, runs Girvan-Newman community detection and a **3-tier
  PageRank fallback** (`safe_pagerank`: `nx.pagerank_numpy` → `nx.pagerank`
  power iteration → `nx.in_degree_centrality`) purely to avoid a scipy
  dependency, colors via stdlib `colorsys` (no seaborn), and renders with
  Pyvis (`curvedCW` edges, arrowheads, edge width scaled 1-12 by weight).

---

## 4. `helpers/` and `ollama/` — Legacy LLM Extraction Path

### 4.1 `ollama/client.py`

A thin `requests`-based wrapper around a local Ollama server
(`OLLAMA_HOST` env var, default `http://localhost:11434`):
- `generate(model_name, prompt, system=None, ...)`: POSTs to `/api/generate`
  with `stream=True`, iterates newline-delimited JSON chunks, accumulates
  `response` text until `done: true`, returns `(full_response, final_context)`.
- `create`, `pull`, `push`, `list`, `copy`, `delete`, `show`, `heartbeat`:
  thin wrappers over the corresponding Ollama REST endpoints
  (`/api/create`, `/api/pull`, `/api/push`, `/api/tags`, `/api/copy`,
  `/api/delete`, `/api/show`, `HEAD /`).

### 4.2 `helpers/prompts.py`

Three prompt functions, all calling `client.generate` and parsing the JSON
response:
- `graphPrompt(input, metadata, model)`: the **legacy generic extraction**
  prompt. Instructs the LLM to extract directed `(source, target,
  relationship, weight 1-10, description)` tuples with explicit
  source=actor/cause, target=recipient/effect semantics, entity names
  normalized to lowercase/singular for downstream merging. No fixed ontology
  — `relationship` is a free-text predicate. Output must be strict JSON list,
  no markdown fences.
- `extractConcepts(prompt, metadata, model)`: even older NER-style extraction
  — entities categorized into `[event, concept, place, object, document,
  organisation, condition, misc]` with an importance score 1-5. Kept only for
  backwards compatibility; not used by either pipeline entry point today.
- `educationalPrompt(input, metadata, model)`: the prompt used by
  `educational_pipeline/pipeline.py` when `use_llm=True`. Asks for JSON with
  `concepts` (`concept_name, aliases, concept_type ∈ {Algorithm, Model,
  Formula, Theory, Component}, definition, evidence`) and `relations`
  (`source, target, relation_type ∈ {Prerequisite, Part-of, Application,
  Extension, Similarity}, weight 1-10 with type-specific suggested ranges,
  evidence`) — i.e. it asks the LLM to directly emit the same controlled
  ontology the rule-based `relation_extractor.py` enforces. Strips markdown
  code fences and attempts a regex JSON-object extraction if raw
  `json.loads` fails.

### 4.3 `helpers/df_helpers.py`

- `documents2Dataframe(documents)`: converts LangChain document chunks into a
  DataFrame with a `chunk_id` (uuid4 hex) column plus each chunk's metadata
  and `page_content` (as `text`).
- `df2ConceptsList` / `concepts2Df`: legacy NER-based extraction path (uses
  `extractConcepts`), kept for backwards compatibility.
- `df2Graph(dataframe, model)`: applies `graphPrompt` to every row's `text`,
  drops rows where the LLM returned invalid JSON (`NaN`), flattens the
  resulting list-of-lists into one flat list of relation dicts.
- `graph2Df(nodes_list)`: converts that flat list into a clean DataFrame,
  validates `{source, target, relationship}` columns are present (raises
  `ValueError` otherwise), lowercases/strips source/target/relationship,
  coerces `weight` to numeric with `fillna(5).clip(1,10)`, ensures a
  `description` column exists.

This legacy path is what `run_pipeline.py --pipeline legacy` calls, and it is
the mechanism behind the older `data_output/*/graph.csv` files still present
in the repo (e.g. `data_output/OrfPathHealth/graph.csv`).

---

## 5. `kg_chatbot/` — FastAPI Backend

### 5.1 `kg_adapter.py` — Knowledge Graph Loader

- `KGNode`: `id, label, description, concept_type, aliases, chapter, section,
  pagerank, degree_centrality, betweenness_centrality, community`.
- `KGEdge`: `source, target, relation_type, weight, evidence`.
- `KnowledgeGraph.from_csv(concepts_csv, relations_csv, concept_stats_csv=None)`:
  - Reads `concepts.csv` (all cols as `str`, NaN→`""`), joins in
    `concept_stats.csv` by `concept_id` if provided (pagerank etc.).
  - Builds an **`nx.MultiDiGraph`** (not a plain DiGraph) specifically because
    a `(source, target)` pair can legitimately carry more than one
    `relation_type` (e.g. both Part-of and Prerequisite) — collapsing to a
    single edge and keeping only the max-weight row would silently destroy a
    Prerequisite edge whenever a same-pair Application/Part-of edge had a
    higher weight, which matters because prerequisite/gap detection depends
    on that specific relation type surviving.
  - Deduplicates on `(src, tgt, relation_type)`, keeping the higher-weight
    occurrence on a repeat.
- `edges_of(concept_id)`: all incident edges (in + out) for a node, across all
  relation types.
- `edge_types_between(source_id, target_id)`: all typed edges directly from
  source→target (may be >1).

### 5.2 `concept_matcher.py` — Question → Concept Matching

- Reuses `educational_pipeline.normalizer.ConceptNormalizer.clean_name` and
  `._is_fuzzy_match` rather than re-implementing name cleaning.
- `_tokenize(text)`: lowercase alpha tokens ≥2 chars minus a chatbot-specific
  stopword list (why/does/do/is/are/what/how/the/a/an/... — different from
  `concept_extractor.STOPWORDS`).
- `match_concept(question, kg)`: for every node in the KG, computes:
  - `name_signal`: 1.0 if the concept's label or any alias literally appears
    (substring) in the question; else 0.75 if `_is_fuzzy_match` on the
    cleaned question vs. the name; else 0.
  - `token_overlap`: Jaccard-like overlap between question tokens and the
    concept name's tokens.
  - `desc_overlap`: same, against the concept's definition tokens.
  - `score = 0.6*name_signal + 0.3*token_overlap + 0.1*desc_overlap`.
  - Picks the highest-scoring node; assigns `confidence` = High (≥0.6) /
    Medium (≥0.3) / Low; returns `None` if the best score is ≤0.05 (no
    confident match).

### 5.3 `subgraph_builder.py` — Localized Subgraph Construction

- Constants: `MAX_DEPTH=2, MAX_PREREQUISITES=6, MAX_RELATED=6`.
- `_bfs_neighborhood(kg, center_id, max_depth)`: plain BFS over the
  **undirected** view (via `edges_of`, which returns both directions) up to
  `max_depth` hops, returning `{concept_id: hop_distance}`.
- `build_localized_subgraph(kg, center_id, question_tokens)`:
  - For every node found within `MAX_DEPTH` (excluding the center itself):
    - Looks at `incoming` (`nid → center`) and `outgoing` (`center → nid`)
      typed edges. **A `Prerequisite` edge from nid→center always classifies
      the node as a prerequisite**, regardless of whether another
      higher-weight relation type exists between the same pair. Otherwise the
      relation type is whichever typed edge (in either direction) has the
      highest weight; falls back to `"related_to"` if no direct edge exists
      (i.e. the node is only reachable via a 2-hop path).
    - Computes a composite ranking score:
      ```
      score = 0.4*best_edge_weight + 0.25*structural_importance
            + 0.2*depth_decay + 0.15*keyword_overlap
      ```
      where `structural_importance = min(1, pagerank*10)` (rescaled since raw
      PageRank values are tiny on small graphs), `depth_decay = 1/depth`, and
      `keyword_overlap` is the Jaccard overlap between the question's tokens
      and the candidate concept's name tokens.
  - Splits candidates into `prerequisites` vs `related` by the
    is-Prerequisite-incoming-edge test, sorts each descending by score, caps
    each list to its `MAX_*` constant, and returns `(prereqs, related)` as
    lists of `RankedConcept(node, relation_type, direction, depth, score)`.

### 5.4 `gap_detector.py` — Knowledge Gap Detection

- `MAX_GAPS=4`, `RELATED_GAP_THRESHOLD=0.5` (a "related" concept is only
  considered a possible gap if its subgraph score is ≥0.5 — most related
  concepts, like an application/example, aren't things you needed
  beforehand).
- `detect_knowledge_gaps(prerequisites, related, conversation)`:
  - Candidate pool = all prerequisites + related concepts scoring above the
    threshold.
  - Skips any concept the `ConversationState` already marks as "known"
    (i.e., previously surfaced as a query's central concept in this
    conversation) — deliberately not re-flagging concepts the user has
    already engaged with.
  - `confidence_score = score + (0.2 if direction == "prerequisite" else 0)`,
    mapped to `High` (≥0.65) / `Medium` (≥0.4) / `Low` confidence bands.
  - Per an explicit design note in the code, gaps are always phrased as
    *possible* (e.g. "This concept is a prerequisite for understanding what
    you asked about"), never as a confirmed fact about the user's knowledge.
  - Sorted High→Medium→Low, capped to `MAX_GAPS`.

### 5.5 `answer_generator.py` — Answer Generation

- `AnswerGenerator` Protocol: `name: str`, `generate(question, center, edges,
  kg_lookup) -> str`.
- `TemplateAnswerGenerator` (`name="template"`): fully offline/deterministic.
  Concatenates the center concept's `description` (definition) with the
  evidence sentence of its single highest-weight incident edge (if that
  evidence isn't already contained in the description). Falls back to a
  generic "no grounded definition extracted yet" message if there's nothing
  to say. Genuinely grounded — nothing is invented.
- `OllamaAnswerGenerator` (`name="ollama"`): builds a context block (concept
  label + definition + up to 5 highest-weight incident edges with their
  relation type, neighbor label, and evidence), sends a "concise teaching
  assistant... using ONLY the context below... 2-4 sentences" prompt to
  `POST {OLLAMA_HOST}/api/generate` with `stream=False`, raises if the
  response is empty (so callers can fall back).
- `get_answer_generator()`: reads `OLLAMA_MODEL` env var — if unset, always
  returns `TemplateAnswerGenerator()`. If set, probes `GET
  {OLLAMA_HOST}/api/tags` to confirm the model is actually pulled (checking
  both the bare name and `<name>:latest`); returns `OllamaAnswerGenerator` only
  if reachable and the model is present, else logs and falls back to the
  template generator. This selection happens once at process startup;
  `main.py` additionally wraps each **per-request** `.generate()` call in a
  try/except that falls back to a fresh `TemplateAnswerGenerator()` if Ollama
  fails mid-session (so a later Ollama outage doesn't 500 the request).

### 5.6 `conversation.py` — In-Memory Conversation State

- `ConversationState`: a `Set[str]` of `concepts_known`; `.knows(id)` /
  `.mark_known(id)`.
- `ConversationStore`: a `Lock`-guarded `Dict[conversation_id, ConversationState]`,
  lazily creating a new state per unseen `conversation_id`.
- Explicitly documented as **process-local and in-memory only** — resets on
  server restart, doesn't scale across multiple backend processes; a
  real deployment would swap in Redis/DB-backed storage.

### 5.7 `schemas.py` — Pydantic Wire Schemas

```python
class QueryRequest(BaseModel):
    question: str
    conversation_id: str

class ConceptRef(BaseModel):
    id: str
    label: str

class GraphNode(BaseModel):
    id: str; label: str; description: str = ""
    type: str  # "central" | "prerequisite" | "related" | "knowledge_gap" | "supporting"
    concept_type: str = ""

class GraphEdge(BaseModel):
    source: str; target: str
    type: str    # relation_type: Prerequisite | Part-of | Application | Extension | Similarity
    weight: float = 0.0

class LocalizedGraph(BaseModel):
    nodes: List[GraphNode]; edges: List[GraphEdge]

class KnowledgeGap(BaseModel):
    concept: ConceptRef; reason: str; confidence: str  # High | Medium | Low

class QueryResponse(BaseModel):
    answer: str
    key_concept: Optional[ConceptRef]
    prerequisites: List[ConceptRef]
    related_concepts: List[ConceptRef]
    knowledge_gaps: List[KnowledgeGap]
    localized_graph: LocalizedGraph
    answer_source: str  # "ollama" | "template"

class HealthResponse(BaseModel):
    status: str; concepts_loaded: int; relations_loaded: int; ollama_available: bool
```

### 5.8 `main.py` — FastAPI App & Endpoints

- `DATA_DIR = <repo_root>/data_output/cureus` (hardcoded to the `cureus`
  dataset — i.e. the backend always serves whatever pipeline output currently
  sits in that folder, regardless of which dataset was last processed).
- CORS: `allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]`
  (the Vite dev server origins), `allow_methods=["*"], allow_headers=["*"]`.
- Module-level singletons created at import time: `kg = KnowledgeGraph.from_csv(...)`,
  `answer_generator = get_answer_generator()`, `conversations = ConversationStore()`.
- **`GET /api/health`**: pings `http://localhost:11434/api/tags` (1s timeout)
  to set `ollama_available`; returns `concepts_loaded = len(kg.nodes)`,
  `relations_loaded = kg.graph.number_of_edges()`.
- **`POST /api/query`** (`QueryRequest → QueryResponse`):
  1. 400 if `question` is blank.
  2. `conv = conversations.get(conversation_id)`.
  3. `match_concept(question, kg)` — if `None`, returns a canned "couldn't
     confidently match" `QueryResponse` with empty graph/gaps and
     `answer_source="template"`.
  4. Otherwise: `build_localized_subgraph(kg, center.id, question_tokens)` →
     `(prereqs, related)`; `detect_knowledge_gaps(prereqs, related, conv)`.
  5. `edges = kg.edges_of(center.id)`; calls `answer_generator.generate(...)`,
     catching any exception to fall back to a fresh
     `TemplateAnswerGenerator()` for that request only.
  6. `conv.mark_known(center.id)` — the just-answered concept won't be
     flagged as a gap in subsequent turns of the same conversation.
  7. Assembles `GraphNode`s: the center node (`type="central"`), each
     prerequisite/related node tagged `"knowledge_gap"` if its id is in the
     detected gap set, else `"prerequisite"`/`"related"`. Edges point
     prerequisite→center and center→related, each carrying the
     `RankedConcept`'s `relation_type` and `score` as `weight`.
  8. Returns the full `QueryResponse`.

Run with `python -m uvicorn kg_chatbot.main:app --reload --port 8000` from the
`LearnKG/` root (required so `kg_chatbot` and `educational_pipeline` resolve
as top-level packages, since `concept_matcher.py` imports
`educational_pipeline.normalizer` directly).

---

## 6. `webapp/` — React Frontend

### 6.1 Tech Stack

From `webapp/package.json`: **React 19.2**, **Vite 8**, **TypeScript ~6.0**,
**TailwindCSS 4** (via `@tailwindcss/vite` plugin — no separate `tailwind.config`
build step), **ReactFlow 11** (`reactflow` — graph canvas/rendering),
**dagre 0.8** (layered graph layout algorithm feeding ReactFlow node
positions), **react-markdown 10** (renders assistant answers as Markdown),
linted with `oxlint`.

`vite.config.ts` proxies `/api/*` to `http://localhost:8000` in dev, which is
why the frontend's fetch calls use bare relative paths (`/api/query`,
`/api/health`) rather than a hardcoded base URL — in production this proxy
doesn't exist, so the built webapp must be served behind something that
performs the same `/api` → backend routing (e.g. a reverse proxy), or the
`fetch` base needs to be reconfigured.

### 6.2 Directory Structure (`webapp/src/`)

```
main.tsx                         # Vite/React entry point
pages/App.tsx                    # Top-level layout: Header + ChatPanel + GraphPanel + InsightsPanel + NodeDetailsPanel
components/Chat/ChatPanel.tsx    # Message list + textarea input (Enter to send, Shift+Enter for newline)
components/Chat/MessageBubble.tsx    # Renders one chat turn (user question / assistant answer, pending/error states)
components/Chat/StructuredAnswer.tsx # Renders the assistant's answer text (markdown) + structured extras
components/Graph/GraphPanel.tsx  # ReactFlow canvas wrapper around the localized_graph from the last response
components/Graph/layout.ts       # layoutGraph(): dagre TB layout → ReactFlow nodes/edges (190x56 node boxes)
components/Graph/ConceptNode.tsx # Custom ReactFlow node renderer (styled by node type/concept_type)
components/Graph/Legend.tsx      # Color/type legend overlay for the graph canvas
components/Insights/InsightsPanel.tsx    # Lists prerequisites / related concepts / knowledge gaps for the latest answer
components/NodeDetails/NodeDetailsPanel.tsx  # Detail popover when a graph node is clicked; "Explain <label>" action
hooks/useConversationId.ts       # Generates/persists a conversation_id (and exposes a reset function)
services/api/queryApi.ts         # postQuery() / getHealth() — thin fetch wrappers, relative /api/* paths
types/api.ts                     # TS interfaces mirroring kg_chatbot/schemas.py exactly (kept in sync by comment convention)
utils/nodeStyles.ts              # Maps GraphNodeType/concept_type to Tailwind/inline styles
index.css                        # Tailwind entry + CSS custom properties (--color-bg, --color-accent, etc.)
```

### 6.3 UI / Data Flow

`App.tsx` holds all app state: `conversationId` (from `useConversationId`),
the running `messages: ChatMessage[]` list, `health`, and `selectedNodeId`.
`latestResponse` is derived as the most recent assistant message's
`QueryResponse`. On `send(question)`:
1. Optimistically appends a user message and a `pending: true` assistant
   placeholder.
2. `postQuery({question, conversation_id})` → on success, fills in
   `response`; on failure, sets `error`.

`GraphPanel` receives `latestResponse?.localized_graph` and re-lays it out via
dagre (`layoutGraph`) every time the graph reference changes, rendering a
`ReactFlow` canvas with a `ConceptNode` custom node type, click-to-select
(`onNodeClick` → `setSelectedNodeId`), and a `Legend` overlay. Clicking a node
opens `NodeDetailsPanel`, which offers an "Explain `<label>`" button that calls
`explainConcept(label)` → `send(\`Explain ${label}\`)`, effectively driving a
new backend query from a graph click. `InsightsPanel` renders prerequisites,
related concepts, and knowledge gaps from the same `latestResponse`, with
concepts clickable to trigger the same `explainConcept` flow.

The `Header` shows live backend health (green/red dot + "`N` concepts loaded"
from `GET /api/health`, polled once on mount).

---

## 7. End-to-End Data Flow

```
 ┌────────────────────┐
 │ data_input/<name>/  │  raw .txt / .pdf textbook chapters
 └─────────┬───────────┘
           │  parse_document()                              [parser.py]
           ▼
   List[ParsedBlock]  (text, page, chapter, section, is_heading)
           │  detect_educational_structures()                [structure_detector.py]
           ▼
   List[StructuredBlock]  (+ block_type: Definition/Theorem/Example/.../Explanation)
           │  create_structure_aware_chunks()                [chunker.py]
           ▼
   List[EducationalChunk]  (chunk_id, text, block_type, chapter, section, page)
           │  extract_concepts_for_chunk() (+ optional educationalPrompt LLM call)
           │  extract_grounded_definition()                  [concept_extractor.py, definition_extractor.py]
           ▼
   ConceptNormalizer registry  → canonical NormalizedConcept per unique concept (C0001, C0002, ...)
           │  extract_relations_from_sentences() + pedagogical_rules + LLM relations + legacy graph.csv ingestion
           ▼                                                 [relation_extractor.py]
   RelationManager.relations → ExtractedRelation list, classified into
   {Prerequisite, Part-of, Application, Extension, Similarity}, AHP-weighted
           │  build_and_save_dataset()                       [dataset_builder.py]
           ▼
 ┌────────────────────────────────────────────┐
 │ data_output/<name>/concepts.csv             │
 │ data_output/<name>/relations.csv            │
 └───────────────┬──────────────────────────────┘
                 │  compute_graph_statistics()                [graph_stats.py]
                 ▼
 ┌────────────────────────────────────────────┐
 │ data_output/<name>/concept_stats.csv        │  (pagerank, centrality, community — precomputed)
 │ data_output/<name>/graph_summary.json       │
 └───────────────┬──────────────────────────────┘
                 │  build_educational_graph()                 [graph_builder.py]
                 ▼
 ┌────────────────────────────────────────────┐
 │ docs/index.html                             │  interactive Pyvis/vis.js graph (offline artifact)
 └────────────────────────────────────────────┘

  ── separately, at chatbot runtime ──

 kg_chatbot.main (FastAPI app import time)
   KnowledgeGraph.from_csv(concepts.csv, relations.csv, concept_stats.csv)   [kg_adapter.py]
           │
 webapp (React, localhost:5173) ──POST /api/query {question, conversation_id}──▶ kg_chatbot (localhost:8000)
           │                                                                       │
           │                                                          match_concept()  [concept_matcher.py]
           │                                                          build_localized_subgraph()  [subgraph_builder.py]
           │                                                          detect_knowledge_gaps()  [gap_detector.py]
           │                                                          answer_generator.generate() (template or Ollama)
           │◀──────────────── QueryResponse {answer, key_concept, prerequisites,
           │                    related_concepts, knowledge_gaps, localized_graph}
           ▼
  GraphPanel (ReactFlow + dagre layout) renders localized_graph
  InsightsPanel renders prerequisites / related_concepts / knowledge_gaps
  ChatPanel renders `answer` as Markdown
```

---

## 8. How to Run (condensed from `RUNNING.md`)

Full details in `/home/dino/finyr/LearnKG/RUNNING.md`; summary:

1. **Install Python deps**: `poetry install && poetry shell` (or
   `conda env create -f environment.yml`), or `docker build -t knowledge-graph .`
   for a JupyterLab-only container.
2. **(Optional) Ollama**: only needed for LLM-based extraction or LLM-based
   chatbot answers; `ollama run zephyr`.
3. **Run the pipeline**:
   ```
   python run_pipeline.py --pipeline educational --dataset cureus --no-llm
   python run_pipeline.py --pipeline educational --dataset cureus --model zephyr:latest
   python run_pipeline.py --pipeline legacy --dataset cureus
   python run_directed.py   # rebuild docs/index.html from existing CSVs only
   ```
4. **Run the chatbot API** (from `LearnKG/` root, so package imports resolve):
   ```
   python -m uvicorn kg_chatbot.main:app --reload --port 8000
   ```
5. **Run the webapp**:
   ```
   cd webapp && npm install && npm run dev   # http://localhost:5173, expects API on :8000
   ```
6. **Tests**: `python test_educational_pipeline.py` — runs the educational
   pipeline end-to-end on `cureus` with `use_llm=False` (deterministic/instant
   offline verification) and validates CSV schema/ontology constraints.

---

## 9. Known Implementation Details Worth Flagging

- **`old_notebooks/`** contains four legacy Jupyter notebooks
  (`concept_graph.ipynb`, `extract_concepts.ipynb`, `relationships.ipynb`,
  `zefyr.ipynb`) predating `educational_pipeline/` — exploratory precursors to
  the current LLM-extraction prompts and graph-building code. Two more
  standalone notebooks, `extract_graph.ipynb` and `ner.ipynb`, sit at the repo
  root outside `old_notebooks/`, apparently even older/duplicate exploratory
  work.
- **Dockerfile** builds a Poetry-based image whose `CMD` launches **JupyterLab**
  (`poetry run jupyter lab --port=8888`), not the FastAPI chatbot server or the
  webapp — i.e. there is currently no containerized path to run `kg_chatbot`
  or `webapp`; Docker here only supports the exploratory-notebook workflow.
- **`pyproject.toml` / `environment.yml` duplication and gaps**: both files
  declare essentially the same legacy-pipeline dependency set (langchain,
  pandas, numpy, pypdf, unstructured, networkx, pyvis, seaborn, jupyterlab,
  yachalk) but **neither lists `fastapi`, `uvicorn`, or `pydantic`**, despite
  `kg_chatbot/` being a FastAPI app built on Pydantic models — meaning a clean
  `poetry install`/`conda env create` alone will not provide what's needed to
  run the backend; those must be installed separately (as the checked-in
  `.venv/bin/{fastapi,uvicorn}` scripts suggest was done ad hoc). The two
  dependency files also drift independently (e.g. `environment.yml` adds
  `tqdm`, which `pyproject.toml` doesn't declare), so they are not kept in
  lockstep.
- **`local_ollama/`** contains a vendored Ollama binary (`ollama`), a tarball
  (`ollama.tgz`), and a log file (`ollama.log`) — a locally-unpacked, ad hoc
  Ollama install kept in-repo rather than the project depending on a
  system-installed Ollama; it is not referenced by any Python code path (all
  Ollama access goes through HTTP to `OLLAMA_HOST`, default
  `localhost:11434`), so this looks like a developer's local artifact
  (arguably should be gitignored rather than committed).
- **`data_output/`** contains a mix of current-format output
  (`cureus/{concepts,relations,concept_stats}.csv` + `graph_summary.json`,
  matching the educational pipeline schema) and legacy-format leftovers from
  earlier runs/datasets (`OrfPathHealth/graph.csv`, `MediumArticles/chunks.csv`,
  `temp/health_india_*.csv`, `legacy_cureus_healthcare_bak/`) — i.e. multiple
  generations of the pipeline's output format coexist on disk, and
  `kg_chatbot/main.py` only ever reads from the hardcoded `data_output/cureus/`
  path, so switching the served dataset requires either overwriting that
  folder or editing `DATA_DIR` in `kg_chatbot/main.py`.
- **`docs/`** holds two generated HTML visualizations, `index.html` (current,
  from `build_educational_graph`) and `graph.html` (likely an older/legacy
  render) — both are build artifacts, not hand-authored.
- **PROJECT_DOCUMENTATION.md** (root) is a shorter, earlier architecture
  write-up covering only `educational_pipeline/` (parser → structure_detector
  → chunker → concept_extractor → relation_extractor → graph outputs); this
  document supersedes it in scope (also covering `kg_chatbot/`, `webapp/`,
  the legacy pipeline, and run/deploy details) but does not contradict its
  module-level descriptions.
- **Legacy vs. educational pipeline bridging**: `pipeline.py` step 7A
  deliberately ingests an existing legacy `graph.csv` (if present in the
  dataset's output folder) and reclassifies its free-text `relationship`
  strings into the 5-type controlled ontology via `classify_relation` — so a
  dataset that was previously processed by the legacy LLM pipeline can be
  "upgraded" into the educational ontology without re-running LLM extraction.
- **Girvan-Newman is recomputed independently in three places**
  (`graph_builder.py`, `graph_stats.py`, and `run_pipeline.py`'s legacy
  branch) with the same "take the second partition level" logic each time —
  there's no shared community-detection helper, so any future change to the
  algorithm would need to be applied in all three call sites.
