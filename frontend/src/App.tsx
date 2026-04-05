import { useState, useEffect } from "react";
import { useUser, useAuth as useClerkAuth } from "@clerk/clerk-react";
import { useAuth as useLocalAuth } from "./auth/AuthContext";
import { Sidebar, type AppView } from "./components/Sidebar";
import { ChatWindow } from "./components/ChatWindow";
import { AuthPage } from "./pages/AuthPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { RulesPage } from "./pages/RulesPage";
import { api, setTokenGetter } from "./api/client";
import type { ChatMessage } from "./types";
import styles from "./App.module.css";

export const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ?? "";
export const clerkConfigured =
  (CLERK_KEY.startsWith("pk_test_") || CLERK_KEY.startsWith("pk_live_"))
  && CLERK_KEY.length > 40
  && !CLERK_KEY.includes("YOUR_CLERK");

// ── Main entry ──────────────────────────────────────────────────────────────

export default function App() {
  return clerkConfigured ? <ClerkBridge /> : <LocalBridge />;
}

// ── Clerk bridge — only rendered when ClerkProvider is in the tree ──────────

function ClerkBridge() {
  const { user, isLoaded } = useUser();
  const { getToken, signOut } = useClerkAuth();

  if (!isLoaded) return null;
  if (!user) return <AuthPage />;

  return (
    <AppShell
      firstName={user.firstName ?? user.username ?? "User"}
      email={user.primaryEmailAddress?.emailAddress ?? ""}
      getToken={() => getToken()}
      signOut={() => signOut()}
    />
  );
}

// ── Local-auth bridge — only rendered when AuthProvider is in the tree ───────

function LocalBridge() {
  const { user, isLoaded, signOut } = useLocalAuth();

  if (!isLoaded) return null;
  if (!user) return <AuthPage />;

  return (
    <AppShell
      firstName={user.firstName}
      email={user.email}
      getToken={async () => null}
      signOut={signOut}
    />
  );
}

// ── Shared app shell ─────────────────────────────────────────────────────────

interface ShellProps {
  firstName: string;
  email: string;
  getToken: () => Promise<string | null>;
  signOut: () => void;
}

function AppShell({ firstName, email, getToken, signOut }: ShellProps) {
  const [view, setView] = useState<AppView>("chat");
  const [chunkCount, setChunkCount] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  useEffect(() => { setTokenGetter(getToken); }, [getToken]);

  useEffect(() => {
    api.readiness().then((r) => setChunkCount(r.vector_store_chunks)).catch(() => {});
  }, []);

  useEffect(() => {
    if (view === "knowledge-base") {
      api.readiness().then((r) => setChunkCount(r.vector_store_chunks)).catch(() => {});
    }
  }, [view]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(), role: "user", content: text.trim(), timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setChatError(null);
    try {
      const res = await api.chat({ message: text.trim(), session_id: sessionId ?? undefined });
      setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        {
          id: res.message_id,
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          triggered_rules: res.triggered_rules,
          reasoning_steps: res.reasoning_steps,
          timestamp: new Date(),
          tokens_used: res.tokens_used,
        },
      ]);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Unexpected error.");
    } finally {
      setIsLoading(false);
    }
  };

  const clearSession = async () => {
    if (sessionId) {
      try { await api.deleteSession(sessionId); } catch { /* best-effort */ }
    }
    setMessages([]); setSessionId(null); setChatError(null);
  };

  return (
    <div className={styles.layout}>
      <Sidebar
        firstName={firstName}
        email={email}
        onSignOut={signOut}
        sessionId={sessionId}
        onNewChat={clearSession}
        view={view}
        onViewChange={setView}
        chunkCount={chunkCount}
      />
      <main className={styles.main}>
        {view === "chat" && (
          <ChatWindow messages={messages} isLoading={isLoading} error={chatError} onSend={sendMessage} />
        )}
        {view === "knowledge-base" && <KnowledgeBasePage onChunkCountChange={setChunkCount} />}
        {view === "rules" && <RulesPage />}
      </main>
    </div>
  );
}
