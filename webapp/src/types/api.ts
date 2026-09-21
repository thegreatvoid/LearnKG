// Mirrors kg_chatbot/schemas.py — keep in sync with the backend contract.

export interface ConceptRef {
  id: string;
  label: string;
}

export type GraphNodeType =
  | "central"
  | "prerequisite"
  | "related"
  | "knowledge_gap"
  | "supporting";

export interface GraphNode {
  id: string;
  label: string;
  description: string;
  type: GraphNodeType;
  concept_type: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface LocalizedGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type ConfidenceLevel = "High" | "Medium" | "Low";

export interface KnowledgeGap {
  concept: ConceptRef;
  reason: string;
  confidence: ConfidenceLevel;
}

export interface QueryResponse {
  answer: string;
  key_concept: ConceptRef | null;
  prerequisites: ConceptRef[];
  related_concepts: ConceptRef[];
  knowledge_gaps: KnowledgeGap[];
  localized_graph: LocalizedGraph;
  answer_source: "ollama" | "template";
}

export interface QueryRequest {
  question: string;
  conversation_id: string;
}

export interface HealthResponse {
  status: string;
  concepts_loaded: number;
  relations_loaded: number;
  ollama_available: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  question?: string;
  response?: QueryResponse;
  pending?: boolean;
  error?: string;
}
