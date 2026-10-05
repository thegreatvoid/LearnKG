import { useEffect, useMemo, useState, type ReactNode } from "react";
import ChatPanel from "../components/Chat/ChatPanel";
import ComparisonView from "../components/Graph/ComparisonView";
import GraphPanel from "../components/Graph/GraphPanel";
import InsightsPanel from "../components/Insights/InsightsPanel";
import NodeDetailsPanel from "../components/NodeDetails/NodeDetailsPanel";
import LearningTrail from "../components/Trail/LearningTrail";
import { useConversationId } from "../hooks/useConversationId";
import { getHealth, postQuery } from "../services/api/queryApi";
import type { ChatMessage, ConceptRef, HealthResponse, LocalizedGraph, QueryResponse } from "../types/api";
import { emptyGraph, mergeGraphs } from "../utils/graphMerge";

type GraphViewMode = "latest" | "cumulative";

export default function App() {
  const [conversationId, resetConversation] = useConversationId();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Cumulative learning map (spec sections 9-13): grows across turns
  // instead of being replaced by each new response.
  const [conversationGraph, setConversationGraph] = useState<LocalizedGraph>(emptyGraph());
  const [trail, setTrail] = useState<ConceptRef[]>([]);
  const [viewMode, setViewMode] = useState<GraphViewMode>("latest");
  const [focusId, setFocusId] = useState<string | null>(null);

  // The latest successful response drives the graph + insights panels.
  const latestResponse: QueryResponse | null =
    [...messages].reverse().find((m) => m.role === "assistant" && m.response)?.response ?? null;

  const exploredIds = useMemo(() => {
    const ids = new Set<string>();
    for (const t of trail) ids.add(t.id);
    return ids;
  }, [trail]);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const pushToTrail = (concept: ConceptRef | null | undefined) => {
    if (!concept) return;
    setTrail((prev) => (prev.some((c) => c.id === concept.id) ? prev : [...prev, concept]));
  };

  const absorbResponse = (response: QueryResponse) => {
    if (response.query_type === "comparison" && response.comparison) {
      const { concept_a, concept_b } = response.comparison;
      setConversationGraph((g) => mergeGraphs(mergeGraphs(g, concept_a.graph), concept_b.graph));
      pushToTrail(concept_a.concept);
      pushToTrail(concept_b.concept);
      setFocusId(concept_a.concept.id);
    } else {
      setConversationGraph((g) => mergeGraphs(g, response.localized_graph));
      pushToTrail(response.key_concept);
      setFocusId(response.key_concept?.id ?? null);
    }
  };

  const send = async (question: string) => {
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", question };
    const pendingMsg: ChatMessage = { id: crypto.randomUUID(), role: "assistant", pending: true };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setSelectedNodeId(null);

    try {
      const response = await postQuery({ question, conversation_id: conversationId });
      setMessages((prev) =>
        prev.map((m) => (m.id === pendingMsg.id ? { ...m, pending: false, response } : m)),
      );
      absorbResponse(response);
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMsg.id
            ? { ...m, pending: false, error: err instanceof Error ? err.message : "Request failed." }
            : m,
        ),
      );
    }
  };

  const explainConcept = (label: string) => {
    send(`Explain ${label}`);
  };

  const focusConcept = (id: string) => {
    setFocusId(id);
    setViewMode("cumulative");
  };

  const clearConversation = () => {
    setMessages([]);
    setSelectedNodeId(null);
    setConversationGraph(emptyGraph());
    setTrail([]);
    setFocusId(null);
    setViewMode("latest");
    resetConversation();
  };

  const clearLearningMap = () => {
    setConversationGraph(emptyGraph());
    setTrail([]);
    setFocusId(null);
    setViewMode("latest");
  };

  const isComparison = latestResponse?.query_type === "comparison" && !!latestResponse.comparison;
  const graphForLatestView = latestResponse?.localized_graph ?? null;

  return (
    <div className="flex h-screen flex-col" style={{ background: "var(--color-bg)" }}>
      <Header health={health} />
      <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[340px_1fr_300px]">
        <div className="min-h-0 border-b lg:border-b-0 lg:border-r" style={{ borderColor: "var(--color-border)" }}>
          <ChatPanel messages={messages} onSend={send} onClear={clearConversation} />
        </div>

        <div className="relative flex min-h-[360px] flex-col">
          {!isComparison && (
            <GraphToolbar
              viewMode={viewMode}
              onChangeViewMode={setViewMode}
              onClearMap={clearLearningMap}
              onFocusLatest={() => setFocusId(latestResponse?.key_concept?.id ?? null)}
            />
          )}
          <div className="relative min-h-0 flex-1">
            {isComparison && latestResponse?.comparison ? (
              <ComparisonView comparison={latestResponse.comparison} onSelectNode={setSelectedNodeId} />
            ) : (
              <GraphPanel
                graph={viewMode === "cumulative" ? conversationGraph : graphForLatestView}
                onSelectNode={setSelectedNodeId}
                focusId={focusId}
                exploredIds={viewMode === "cumulative" ? exploredIds : undefined}
                fitKey={viewMode === "cumulative" ? "cumulative" : `latest-${focusId ?? "none"}`}
              />
            )}
            {latestResponse && selectedNodeId && !isComparison && (
              <NodeDetailsPanel
                response={latestResponse}
                nodeId={selectedNodeId}
                onClose={() => setSelectedNodeId(null)}
                onExplain={explainConcept}
              />
            )}
          </div>
        </div>

        <div className="flex min-h-0 flex-col border-t lg:border-t-0 lg:border-l" style={{ borderColor: "var(--color-border)" }}>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <InsightsPanel response={latestResponse} onSelectConcept={explainConcept} />
          </div>
          <LearningTrail trail={trail} focusId={focusId} onFocus={focusConcept} />
        </div>
      </main>
    </div>
  );
}

function GraphToolbar({
  viewMode,
  onChangeViewMode,
  onClearMap,
  onFocusLatest,
}: {
  viewMode: GraphViewMode;
  onChangeViewMode: (m: GraphViewMode) => void;
  onClearMap: () => void;
  onFocusLatest: () => void;
}) {
  return (
    <div
      className="flex items-center justify-between gap-2 border-b px-3 py-1.5"
      style={{ borderColor: "var(--color-border)" }}
    >
      <div className="flex gap-1 rounded-lg border p-0.5" style={{ borderColor: "var(--color-border)" }}>
        <ToggleButton active={viewMode === "latest"} onClick={() => onChangeViewMode("latest")}>
          Latest Query
        </ToggleButton>
        <ToggleButton active={viewMode === "cumulative"} onClick={() => onChangeViewMode("cumulative")}>
          Learning Map
        </ToggleButton>
      </div>
      <div className="flex gap-2">
        {viewMode === "cumulative" && (
          <SmallButton onClick={onFocusLatest}>Focus current concept</SmallButton>
        )}
        <SmallButton onClick={onClearMap}>Clear learning map</SmallButton>
      </div>
    </div>
  );
}

function ToggleButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
      style={{
        background: active ? "var(--color-accent)" : "transparent",
        color: active ? "#fff" : "var(--color-text-muted)",
      }}
    >
      {children}
    </button>
  );
}

function SmallButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="rounded-md border px-2.5 py-1 text-xs font-medium hover:opacity-80"
      style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}
    >
      {children}
    </button>
  );
}

function Header({ health }: { health: HealthResponse | null }) {
  const ok = health?.status === "ok";
  return (
    <header
      className="flex items-center justify-between border-b px-4 py-2.5"
      style={{ borderColor: "var(--color-border)" }}
    >
      <div className="flex items-center gap-2">
        <div className="h-6 w-6 rounded-md" style={{ background: "var(--color-accent)" }} />
        <span className="text-sm font-semibold">KnowledgeGraph AI</span>
      </div>
      <div className="flex items-center gap-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: ok ? "#16a34a" : "#dc2626" }}
        />
        {ok ? `${health?.concepts_loaded} concepts loaded` : "backend unreachable"}
      </div>
    </header>
  );
}
