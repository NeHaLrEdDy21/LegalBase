import { useState, useCallback, useRef } from "react";
import { api } from "../api/client";
import type { ChatMessage } from "../types";

function uuid() {
  return crypto.randomUUID();
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      abortRef.current = new AbortController();

      try {
        const response = await api.chat({
          message: text.trim(),
          session_id: sessionId ?? undefined,
        });

        setSessionId(response.session_id);

        const assistantMsg: ChatMessage = {
          id: response.message_id,
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          triggered_rules: response.triggered_rules,
          reasoning_steps: response.reasoning_steps,
          timestamp: new Date(),
          tokens_used: response.tokens_used,
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "An unexpected error occurred.";
        setError(msg);
      } finally {
        setIsLoading(false);
        abortRef.current = null;
      }
    },
    [isLoading, sessionId]
  );

  const clearSession = useCallback(async () => {
    if (sessionId) {
      try {
        await api.deleteSession(sessionId);
      } catch {
        // best-effort
      }
    }
    setMessages([]);
    setSessionId(null);
    setError(null);
  }, [sessionId]);

  return { messages, sessionId, isLoading, error, sendMessage, clearSession };
}
