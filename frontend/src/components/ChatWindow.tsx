import { useEffect, useRef, useState, useCallback } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { ChatInput } from "./ChatInput";
import styles from "./ChatWindow.module.css";

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  onSend: (text: string) => void;
}

const SUGGESTIONS = [
  { icon: "⚖️", text: "What is the neighbour principle from Donoghue v Stevenson?" },
  { icon: "📋", text: "Explain the elements of negligence in tort law." },
  { icon: "🏛️", text: "What is the doctrine of precedent (stare decisis)?" },
  { icon: "💧", text: "How does the rule in Rylands v Fletcher apply?" },
];

export function ChatWindow({ messages, isLoading, error, onSend }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(dist > 200);
  };

  const isEmpty = messages.length === 0;

  return (
    <div className={styles.container}>
      {/* ── Header ──────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}><GavelIcon /></div>
          <div>
            <span className={styles.headerTitle}>LegalMind</span>
            <span className={styles.headerSub}>AI-Powered Legal Research</span>
          </div>
        </div>
        <div className={styles.headerStatus}>
          <span className={styles.statusDot} />
          <span>Online</span>
        </div>
      </header>

      {/* ── Messages ────────────────────────────── */}
      <div className={styles.messages} ref={scrollRef} onScroll={handleScroll}>
        {isEmpty && !isLoading && (
          <div className={styles.empty}>
            <div className={styles.emptyOrb} aria-hidden>
              <ScalesIcon3D />
            </div>
            <div className={styles.emptyText}>
              <h2>Legal Research Assistant</h2>
              <p>Ask about case law, statutes, legal principles, or upload documents to analyse.</p>
            </div>
            <div className={styles.suggestions}>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  className={styles.suggestion}
                  onClick={() => onSend(s.text)}
                >
                  <span className={styles.sugIcon}>{s.icon}</span>
                  <span>{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* ── Scroll btn ──────────────────────────── */}
      {showScrollBtn && (
        <button className={styles.scrollBtn} onClick={scrollToBottom} aria-label="Scroll to bottom">
          <ChevronDownIcon />
        </button>
      )}

      {/* ── Error banner ────────────────────────── */}
      {error && (
        <div className={styles.errorBanner} role="alert">
          <ErrorIcon />
          {error}
        </div>
      )}

      {/* ── Input ───────────────────────────────── */}
      <div className={styles.inputArea}>
        <ChatInput onSend={onSend} disabled={isLoading} />
        <p className={styles.disclaimer}>
          LegalMind provides information only — not legal advice. Always consult a qualified solicitor.
        </p>
      </div>
    </div>
  );
}

function ScalesIcon3D() {
  return (
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.4"
         strokeLinecap="round" strokeLinejoin="round" width="52" height="52">
      <line x1="24" y1="6" x2="24" y2="42" />
      <line x1="10" y1="13" x2="38" y2="13" />
      <line x1="14" y1="13" x2="8"  y2="26" />
      <line x1="14" y1="13" x2="20" y2="26" />
      <line x1="34" y1="13" x2="28" y2="30" />
      <line x1="34" y1="13" x2="40" y2="30" />
      <path d="M5 26 Q14 32 23 26" />
      <path d="M25 30 Q34 36 43 30" />
      <path d="M18 42 L30 42 L29 44 L19 44 Z" />
    </svg>
  );
}

function GavelIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <path d="M14 6l-1-1L7 11l1 1" />
      <path d="M3 21l7-7" />
      <path d="M10 9l5 5-5 5-5-5 5-5z" />
      <path d="M17 6l1 1-6 6-1-1" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="14" height="14" style={{flexShrink:0}}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}
