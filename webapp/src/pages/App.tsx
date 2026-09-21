import { useEffect, useState } from "react";
import ChatPanel from "../components/Chat/ChatPanel";
import GraphPanel from "../components/Graph/GraphPanel";
import InsightsPanel from "../components/Insights/InsightsPanel";
import NodeDetailsPanel from "../components/NodeDetails/NodeDetailsPanel";
import { useConversationId } from "../hooks/useConversationId";
import { getHealth, postQuery } from "../services/api/queryApi";
import type { ChatMessage, HealthResponse, QueryResponse } from "../types/api";

export default function App() {
  const [conversationId, resetConversation] = useConversationId();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // The latest successful response drives the graph + insights panels.
  const latestResponse: QueryResponse | null =
    [...messages].reverse().find((m) => m.role === "assistant" && m.response)?.response ?? null;

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

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

  const clearConversation = () => {
    setMessages([]);
    setSelectedNodeId(null);
    resetConversation();
  };

  return (
    <div className="flex h-screen flex-col" style={{ background: "var(--color-bg)" }}>
      <Header health={health} />
      <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[340px_1fr_300px]">
        <div className="min-h-0 border-b lg:border-b-0 lg:border-r" style={{ borderColor: "var(--color-border)" }}>
          <ChatPanel messages={messages} onSend={send} onClear={clearConversation} />
        </div>

        <div className="relative min-h-[360px]">
          <GraphPanel graph={latestResponse?.localized_graph ?? null} onSelectNode={setSelectedNodeId} />
          {latestResponse && selectedNodeId && (
            <NodeDetailsPanel
              response={latestResponse}
              nodeId={selectedNodeId}
              onClose={() => setSelectedNodeId(null)}
              onExplain={explainConcept}
            />
          )}
        </div>

        <div className="min-h-0 border-t lg:border-t-0 lg:border-l" style={{ borderColor: "var(--color-border)" }}>
          <InsightsPanel response={latestResponse} onSelectConcept={explainConcept} />
        </div>
      </main>
    </div>
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
