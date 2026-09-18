import type { ChatMessage } from "../../types/api";
import StructuredAnswer from "./StructuredAnswer";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[85%] rounded-2xl rounded-br-sm px-3.5 py-2 text-sm"
          style={{ background: "var(--color-accent)", color: "#fff" }}
        >
          {message.question}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div
        className="max-w-[92%] rounded-2xl rounded-bl-sm border px-3.5 py-3"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
      >
        {message.pending && <TypingIndicator />}
        {message.error && (
          <p className="text-sm" style={{ color: "var(--color-gap)" }}>
            {message.error}
          </p>
        )}
        {message.response && <StructuredAnswer response={message.response} />}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full"
          style={{ background: "var(--color-text-muted)", animationDelay: `${i * 0.12}s` }}
        />
      ))}
    </div>
  );
}
