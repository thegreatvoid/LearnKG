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
  | "supporting"
  | "parent";

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

export type QueryType = "normal" | "comparison";

export interface ComparisonSide {
  concept: ConceptRef;
  parent_chain: ConceptRef[];
  prerequisites: ConceptRef[];
  related_concepts: ConceptRef[];
  knowledge_gaps: KnowledgeGap[];
  graph: LocalizedGraph;
}

export interface ComparisonResult {
  concept_a: ComparisonSide;
  concept_b: ComparisonSide;
  summary: string[];
}

export interface QueryResponse {
  answer: string;
  key_concept: ConceptRef | null;
  prerequisites: ConceptRef[];
  related_concepts: ConceptRef[];
  knowledge_gaps: KnowledgeGap[];
  localized_graph: LocalizedGraph;
  answer_source: "ollama" | "template";
  // Additive (older responses/mocks without these still satisfy the type
  // since the backend always sends them, but keep them optional here in
  // case this type is ever used to describe partial/test fixtures).
  query_type: QueryType;
  parent_chain: ConceptRef[];
  comparison: ComparisonResult | null;
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
