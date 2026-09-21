"""
Pydantic response/request models for the /api/query contract (see project
plan section 13). Kept separate from educational_pipeline's dataclasses
since this is the wire format, not the internal KG representation.
"""

from typing import List, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    conversation_id: str


class ConceptRef(BaseModel):
    id: str
    label: str


class GraphNode(BaseModel):
    id: str
    label: str
    description: str = ""
    type: str  # "central" | "prerequisite" | "related" | "knowledge_gap" | "supporting"
    concept_type: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # relation_type from the KG (Prerequisite, Part-of, Application, Extension, Similarity)
    weight: float = 0.0


class LocalizedGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class KnowledgeGap(BaseModel):
    concept: ConceptRef
    reason: str
    confidence: str  # "High" | "Medium" | "Low"


class QueryResponse(BaseModel):
    answer: str
    key_concept: Optional[ConceptRef]
    prerequisites: List[ConceptRef]
    related_concepts: List[ConceptRef]
    knowledge_gaps: List[KnowledgeGap]
    localized_graph: LocalizedGraph
    answer_source: str  # "ollama" | "template" — surfaced for transparency/debugging


class HealthResponse(BaseModel):
    status: str
    concepts_loaded: int
    relations_loaded: int
    ollama_available: bool
