import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../../types/api";
import MessageBubble from "./MessageBubble";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (question: string) => void;
  onClear: () => void;
}

export default function ChatPanel({ messages, onSend, onClear }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    const q = draft.trim();
    if (!q) return;
    onSend(q);
    setDraft("");
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-2.5" style={{ borderColor: "var(--color-border)" }}>
        <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
          Conversation
        </h2>
        {messages.length > 0 && (
          <button
            onClick={onClear}
            className="text-xs hover:opacity-70"
            style={{ color: "var(--color-text-muted)" }}
          >
            Clear
          </button>
        )}
      </div>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && (
          <p className="mt-6 text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
            Ask about a concept, e.g. “Why do we need gradient descent?”
          </p>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>

      <div className="border-t p-3" style={{ borderColor: "var(--color-border)" }}>
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask a question..."
            className="flex-1 resize-none rounded-lg border px-3 py-2 text-sm outline-none"
            style={{ borderColor: "var(--color-border)", background: "var(--color-bg)", color: "var(--color-text)" }}
          />
          <button
            onClick={submit}
            disabled={!draft.trim()}
            className="rounded-lg px-3.5 py-2 text-sm font-medium text-white disabled:opacity-40"
            style={{ background: "var(--color-accent)" }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
