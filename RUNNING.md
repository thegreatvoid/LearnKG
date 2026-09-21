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

## Typical end-to-end flow

```bash
cd LearnKG
poetry install
python run_pipeline.py --pipeline educational --dataset cureus --no-llm
python -m uvicorn kg_chatbot.main:app --reload --port 8000 &
cd webapp && npm install && npm run dev
```
