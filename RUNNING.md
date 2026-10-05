# Running This Project

This repo has three parts you can run independently:

1. **Knowledge graph pipeline** (Python) — turns source documents into a graph (`concepts.csv`, `relations.csv`, `docs/index.html`).
2. **Chatbot API** (FastAPI) — serves Q&A over the generated graph.
3. **Webapp** (React + Vite) — frontend UI for the chatbot / graph explorer.

All commands below assume you `cd LearnKG` first.

## Prerequisites

- Python 3.11
- [Poetry](https://python-poetry.org/) (or conda, see alternative below)
- Node.js 18+ (for the webapp)
- [Ollama](https://ollama.ai) — only needed if you want LLM-based extraction instead of the rule-based pipeline
- Docker — optional, for the containerized JupyterLab environment

## 1. Install Python dependencies

**Option A — Poetry (recommended):**
```bash
cd LearnKG
poetry install
poetry shell
```

**Option B — conda:**
```bash
cd LearnKG
conda env create -f environment.yml
conda activate knowledge-graph
```

**Option C — Docker (JupyterLab only):**
```bash
cd LearnKG
docker build -t knowledge-graph .
docker run -p 8888:8888 knowledge-graph
```
Then open the JupyterLab URL printed in the container logs.

## 2. (Optional) Set up Ollama for LLM extraction

Only required if you run the pipeline with an LLM model instead of `--no-llm`.

```bash
# install from https://ollama.ai, then:
ollama run zephyr
```

## 3. Run the knowledge graph pipeline

Generates concepts/relations CSVs and an interactive graph at `docs/index.html`.

```bash
# Educational pipeline (default), rule-based (no LLM calls):
python run_pipeline.py --pipeline educational --dataset cureus --no-llm

# Educational pipeline using a local Ollama model:
python run_pipeline.py --pipeline educational --dataset cureus --model zephyr:latest

# Legacy (original) pipeline:
python run_pipeline.py --pipeline legacy --dataset cureus
```

Datasets live under `data_input/<dataset_name>/`; outputs are written to `data_output/<dataset_name>/`.

Windows convenience scripts are also available: `run_educational.bat`, `run_directed.bat`.

To just rebuild the HTML visualization from an already-generated `graph.csv` / `concepts.csv`/`relations.csv` (no re-extraction):
```bash
python run_directed.py
```

Open `docs/index.html` in a browser to view the graph.

## 4. Run the chatbot API

The API reads the graph produced in step 3 from `data_output/cureus/`.

```bash
cd LearnKG
python -m uvicorn kg_chatbot.main:app --reload --port 8000
```

- Health check: `GET http://localhost:8000/api/health`
- Query endpoint: `POST http://localhost:8000/api/query`

Must be run from the `LearnKG/` directory so `kg_chatbot` and `educational_pipeline` resolve as top-level packages.

## 5. Run the webapp

```bash
cd LearnKG/webapp
npm install
npm run dev
```

Opens at `http://localhost:5173` and expects the chatbot API running at `http://localhost:8000`.

Other webapp scripts:
```bash
npm run build     # production build
npm run preview   # preview the production build
npm run lint      # lint with oxlint
```

## 6. Run tests

```bash
cd LearnKG
python test_educational_pipeline.py
```

## 7. Evaluating chatbot quality

`evaluate_chatbot.py` auto-generates a question set directly from the KG's own grounded concept definitions (no external dataset needed), runs each question through the real chatbot retrieval/answer pipeline, and reports retrieval accuracy plus an answer-groundedness "judge" score:

```bash
cd LearnKG
python evaluate_chatbot.py                          # fully offline: template answers + token-overlap judge
OLLAMA_MODEL=zephyr:latest python evaluate_chatbot.py   # LLM-judge variant, if Ollama is running locally
```

Full per-question results are written to `data_output/<dataset>/eval_results.json`.

## 8. MINE-1 methodology eval (embedding retrieval + 2-hop context + LLM judge)

`evaluate_mine1.py` reproduces kg-gen's MINE benchmark methodology (`kg-gen/experiments/MINE/_1_evaluation.py`) directly against LearnKG's own KG: embeds every concept with `sentence-transformers`, retrieves the top-k nodes most similar to a question, expands each to its 2-hop neighborhood, and has an LLM (or a deterministic fallback) judge whether that retrieved context actually grounds the expected answer — distinct from `evaluate_chatbot.py`, which judges a generated answer rather than raw retrieved context.

Requires `sentence-transformers` (not in `pyproject.toml`/`environment.yml` — install separately: `pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install sentence-transformers` to get a CPU-only torch rather than the much larger GPU/CUDA build). Downloads the `all-MiniLM-L6-v2` model from Hugging Face on first run.

```bash
cd LearnKG
python evaluate_mine1.py
OLLAMA_MODEL=zephyr:latest python evaluate_mine1.py   # LLM-judge variant
```

Full per-question results (including the retrieved context block) are written to `data_output/<dataset>/mine1_eval_results.json`.

## 9. Validating relations (wanted vs. unwanted, and likely-missing)

`validate_relations.py` checks `relations.csv` two ways:
- **Wanted vs. unwanted**: every relation carries verbatim `evidence`, so each one is checked structurally (referential integrity, no self-loops/duplicates, weight range, valid ontology type) and semantically (does the evidence actually mention both the source and target concept, and contain a keyword that supports the assigned relation type?). Optionally adds an LLM-as-judge pass (Ollama) asking directly whether the evidence supports the relation claim.
- **Likely missing**: concept pairs that co-occur in the same source chunk but have no relation between them in either direction are reported as review candidates.

```bash
cd LearnKG
python validate_relations.py
OLLAMA_MODEL=zephyr:latest python validate_relations.py   # adds the LLM-judge pass
```

Full results written to `data_output/<dataset>/relation_validation.json`.

## Typical end-to-end flow

```bash
cd LearnKG
poetry install
python run_pipeline.py --pipeline educational --dataset cureus --no-llm
python -m uvicorn kg_chatbot.main:app --reload --port 8000 &
cd webapp && npm install && npm run dev
```

## Verifying it's running

```bash
curl -s http://localhost:8000/api/health
# {"status":"ok","concepts_loaded":33,"relations_loaded":158,"ollama_available":true}
```

Open `http://localhost:5173` for the chat UI, or hit the API directly:

```bash
# Normal query
curl -s -X POST http://localhost:8000/api/query -H 'Content-Type: application/json' \
  -d '{"question":"What is Gradient Descent?","conversation_id":"demo"}'

# Comparison query (works for any concept pair the KG contains, not just this example)
curl -s -X POST http://localhost:8000/api/query -H 'Content-Type: application/json' \
  -d '{"question":"What is the difference between RMSProp and Adam?","conversation_id":"demo"}'
```

## Chatbot features (query API)

The `/api/query` response now includes, in addition to the original `answer`/`prerequisites`/`localized_graph` fields:

- `query_type`: `"normal"` or `"comparison"`, auto-detected from phrasing like "X vs Y" or "difference between X and Y".
- `parent_chain`: the concept's linear ancestor path (chapter → section → Part-of hierarchy) derived from the existing knowledge graph — no separate concept list involved.
- `comparison`: for comparison queries, two independently-built localized subgraphs (each with its own parent chain, neighbors, and knowledge gaps) plus a KG-grounded comparison summary.

In the webapp, the graph panel has a **Latest Query / Learning Map** toggle — "Learning Map" accumulates concepts across the whole conversation instead of replacing the graph on every question — plus a **Learning Trail** panel listing concepts queried so far (click one to refocus the map on it).
