"""
FastAPI app exposing POST /api/query and GET /api/health for the localized
knowledge-graph learning chatbot. Wires kg_adapter, concept_matcher,
subgraph_builder, gap_detector, and answer_generator together against the
domain KG already produced by educational_pipeline (data_output/cureus/).

Run with:  python -m uvicorn kg_chatbot.main:app --reload --port 8000
(from the LearnKG/ directory, so both `kg_chatbot` and `educational_pipeline`
resolve as top-level packages).
"""

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .answer_generator import TemplateAnswerGenerator, get_answer_generator
from .concept_matcher import _tokenize, match_concept
from .conversation import ConversationStore
from .gap_detector import detect_knowledge_gaps
from .kg_adapter import KnowledgeGraph
from .schemas import (
    ConceptRef,
    GraphEdge,
    GraphNode,
    HealthResponse,
    LocalizedGraph,
    QueryRequest,
    QueryResponse,
)
from .subgraph_builder import build_localized_subgraph

DATA_DIR = Path(__file__).resolve().parent.parent / "data_output" / "deep_learning"

app = FastAPI(title="KnowledgeGraph AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

kg = KnowledgeGraph.from_csv(
    concepts_csv=DATA_DIR / "concepts.csv",
    relations_csv=DATA_DIR / "relations.csv",
    concept_stats_csv=DATA_DIR / "concept_stats.csv",
)
answer_generator = get_answer_generator()
conversations = ConversationStore()


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ollama_ok = False
    try:
        import requests

        requests.get("http://localhost:11434/api/tags", timeout=1.0).raise_for_status()
        ollama_ok = True
    except Exception:
        pass
    return HealthResponse(
        status="ok",
        concepts_loaded=len(kg.nodes),
        relations_loaded=kg.graph.number_of_edges(),
        ollama_available=ollama_ok,
    )


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    conv = conversations.get(req.conversation_id)

    match = match_concept(req.question, kg)
    if match is None:
        return QueryResponse(
            answer=(
                "I couldn't confidently match your question to a concept in this "
                "knowledge graph. Try mentioning a specific term from the course material."
            ),
            key_concept=None,
            prerequisites=[],
            related_concepts=[],
            knowledge_gaps=[],
            localized_graph=LocalizedGraph(nodes=[], edges=[]),
            answer_source="template",
        )

    center = match.node
    question_tokens = _tokenize(req.question)
    prereqs, related = build_localized_subgraph(kg, center.id, question_tokens)
    gaps = detect_knowledge_gaps(prereqs, related, conv)
    gap_ids = {g.concept.id for g in gaps}

    edges = kg.edges_of(center.id)
    try:
        answer_text = answer_generator.generate(req.question, center, edges, kg.get)
        source = answer_generator.name
    except Exception as exc:
        print(f"[kg_chatbot] answer_generator failed ({exc}); falling back to template for this request.")
        answer_text = TemplateAnswerGenerator().generate(req.question, center, edges, kg.get)
        source = "template"

    # Mark the central concept as "known" going forward in this
    # conversation, so a later question about it stops flagging it as a gap.
    conv.mark_known(center.id)

    graph_nodes: List[GraphNode] = [
        GraphNode(id=center.id, label=center.label, description=center.description,
                   type="central", concept_type=center.concept_type)
    ]
    graph_edges: List[GraphEdge] = []

    for c in prereqs:
        node_type = "knowledge_gap" if c.node.id in gap_ids else "prerequisite"
        graph_nodes.append(GraphNode(
            id=c.node.id, label=c.node.label, description=c.node.description,
            type=node_type, concept_type=c.node.concept_type,
        ))
        graph_edges.append(GraphEdge(source=c.node.id, target=center.id, type=c.relation_type, weight=c.score))

    for c in related:
        node_type = "knowledge_gap" if c.node.id in gap_ids else "related"
        graph_nodes.append(GraphNode(
            id=c.node.id, label=c.node.label, description=c.node.description,
            type=node_type, concept_type=c.node.concept_type,
        ))
        graph_edges.append(GraphEdge(source=center.id, target=c.node.id, type=c.relation_type, weight=c.score))

    return QueryResponse(
        answer=answer_text,
        key_concept=ConceptRef(id=center.id, label=center.label),
        prerequisites=[ConceptRef(id=c.node.id, label=c.node.label) for c in prereqs],
        related_concepts=[ConceptRef(id=c.node.id, label=c.node.label) for c in related],
        knowledge_gaps=gaps,
        localized_graph=LocalizedGraph(nodes=graph_nodes, edges=graph_edges),
        answer_source=source,
    )
