import { useState } from "react";

const STORAGE_KEY = "kg-chatbot-conversation-id";

function createId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `conv-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** Persists a per-tab conversation_id in sessionStorage so the backend's
 * in-memory conversation state (known concepts) survives a page reload
 * within the same tab, per project spec section 10. */
export function useConversationId(): [string, () => void] {
  const [id, setId] = useState<string>(() => {
    try {
      const existing = sessionStorage.getItem(STORAGE_KEY);
      if (existing) return existing;
    } catch {
      // sessionStorage unavailable (private mode, etc.) — fall through
    }
    const fresh = createId();
    try {
      sessionStorage.setItem(STORAGE_KEY, fresh);
    } catch {
      // ignore
    }
    return fresh;
  });

  const reset = () => {
    const fresh = createId();
    try {
      sessionStorage.setItem(STORAGE_KEY, fresh);
    } catch {
      // ignore
    }
    setId(fresh);
  };

  return [id, reset];
}
