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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .answer_generator import TemplateAnswerGenerator, get_answer_generator
from .comparison import build_comparison_side, build_comparison_summary
from .concept_matcher import _tokenize, match_concept
from .conversation import ConversationStore
from .gap_detector import detect_knowledge_gaps
from .graph_assembly import assemble_localized_graph
from .hierarchy import build_parent_chain
from .intent_classifier import classify_query
from .kg_adapter import KnowledgeGraph
from .schemas import (
    ComparisonResult,
    ComparisonSideResponse,
    ConceptRef,
    HealthResponse,
    LocalizedGraph,
    QueryRequest,
    QueryResponse,
)
from .subgraph_builder import build_localized_subgraph

DATA_DIR = Path(__file__).resolve().parent.parent / "data_output" / "cureus"

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

    intent = classify_query(req.question)
    if intent.query_type == "comparison":
        return _handle_comparison_query(intent, conv)

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

    parent_chain = build_parent_chain(kg, center.id)
    graph_nodes, graph_edges = assemble_localized_graph(center, prereqs, related, gap_ids, parent_chain)

    return QueryResponse(
        answer=answer_text,
        key_concept=ConceptRef(id=center.id, label=center.label),
        prerequisites=[ConceptRef(id=c.node.id, label=c.node.label) for c in prereqs],
        related_concepts=[ConceptRef(id=c.node.id, label=c.node.label) for c in related],
        knowledge_gaps=gaps,
        localized_graph=LocalizedGraph(nodes=graph_nodes, edges=graph_edges),
        answer_source=source,
        query_type="normal",
        parent_chain=[ConceptRef(id=c.id, label=c.label) for c in parent_chain],
    )


def _handle_comparison_query(intent, conv) -> QueryResponse:
    """COMPARISON_QUERY path (project spec sections 15-20): two
    independently-built localized graphs (each with its own parent chain,
    2-hop neighborhood, and knowledge gaps) plus a KG-grounded comparison
    summary. Falls back to the normal single-concept path if only one side
    of the comparison actually resolves to a KG concept, since that means
    the "comparison" phrasing was a false positive."""
    side_a = build_comparison_side(kg, intent.phrase_a, conv)
    side_b = build_comparison_side(kg, intent.phrase_b, conv)

    if side_a is None or side_b is None:
        resolved = side_a or side_b
        if resolved is None:
            return QueryResponse(
                answer=(
                    "I couldn't confidently match either side of that comparison to a "
                    "concept in this knowledge graph. Try naming specific terms from the course material."
                ),
                key_concept=None,
                prerequisites=[],
                related_concepts=[],
                knowledge_gaps=[],
                localized_graph=LocalizedGraph(nodes=[], edges=[]),
                answer_source="template",
            )
        # Only one side resolved — answer about that one concept instead of
        # silently guessing at the other.
        center = resolved.match.node
        gap_ids = {g.concept.id for g in resolved.knowledge_gaps}
        nodes, edges = assemble_localized_graph(
            center, resolved.prerequisites, resolved.related, gap_ids, resolved.parent_chain
        )
        conv.mark_known(center.id)
        answer_text = TemplateAnswerGenerator().generate(center.label, center, kg.edges_of(center.id), kg.get)
        return QueryResponse(
            answer=answer_text,
            key_concept=ConceptRef(id=center.id, label=center.label),
            prerequisites=[ConceptRef(id=c.node.id, label=c.node.label) for c in resolved.prerequisites],
            related_concepts=[ConceptRef(id=c.node.id, label=c.node.label) for c in resolved.related],
            knowledge_gaps=resolved.knowledge_gaps,
            localized_graph=LocalizedGraph(nodes=nodes, edges=edges),
            answer_source="template",
            query_type="normal",
            parent_chain=[ConceptRef(id=c.id, label=c.label) for c in resolved.parent_chain],
        )

    conv.mark_known(side_a.match.node.id)
    conv.mark_known(side_b.match.node.id)

    def _to_response_side(side) -> ComparisonSideResponse:
        gap_ids = {g.concept.id for g in side.knowledge_gaps}
        nodes, edges = assemble_localized_graph(
            side.match.node, side.prerequisites, side.related, gap_ids, side.parent_chain
        )
        return ComparisonSideResponse(
            concept=ConceptRef(id=side.match.node.id, label=side.match.node.label),
            parent_chain=[ConceptRef(id=c.id, label=c.label) for c in side.parent_chain],
            prerequisites=[ConceptRef(id=c.node.id, label=c.node.label) for c in side.prerequisites],
            related_concepts=[ConceptRef(id=c.node.id, label=c.node.label) for c in side.related],
            knowledge_gaps=side.knowledge_gaps,
            graph=LocalizedGraph(nodes=nodes, edges=edges),
        )

    summary = build_comparison_summary(side_a, side_b)
    response_a = _to_response_side(side_a)
    response_b = _to_response_side(side_b)

    answer_text = "\n".join(f"- {line}" for line in summary)

    return QueryResponse(
        answer=answer_text,
        # Legacy top-level fields mirror side A so clients that don't yet
        # know about `comparison` still render something sensible.
        key_concept=response_a.concept,
        prerequisites=response_a.prerequisites,
        related_concepts=response_a.related_concepts,
        knowledge_gaps=response_a.knowledge_gaps,
        localized_graph=response_a.graph,
        answer_source="template",
        query_type="comparison",
        parent_chain=response_a.parent_chain,
        comparison=ComparisonResult(concept_a=response_a, concept_b=response_b, summary=summary),
    )
