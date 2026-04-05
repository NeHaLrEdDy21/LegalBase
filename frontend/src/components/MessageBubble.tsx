import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, TriggeredRule, ReasoningStep } from "../types";
import styles from "./MessageBubble.module.css";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className={`${styles.wrapper} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.avatar} title={isUser ? "You" : "LegalMind AI"}>
        {isUser ? <UserIcon /> : <AIIcon />}
      </div>

      <div className={styles.bubble}>
        <div className={styles.content}>
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {message.sources && message.sources.length > 0 && (
          <details className={styles.sources}>
            <summary>
              <BookIcon />
              {message.sources.length} source{message.sources.length !== 1 ? "s" : ""}
            </summary>
            <ul>
              {message.sources.map((src, i) => {
                const pct = Math.round(src.relevance_score * 100);
                const scoreColor = pct >= 80 ? "#22c55e" : pct >= 60 ? "#f59e0b" : "#94a3b8";
                return (
                  <li key={i}>
                    <div className={styles.sourceHeader}>
                      <span className={styles.sourceFile}>
                        <DocIcon />
                        {src.filename}
                      </span>
                      <span className={styles.sourceScore} style={{ color: scoreColor }}>
                        {pct}%
                      </span>
                    </div>
                    <div className={styles.relevanceBar}>
                      <div
                        className={styles.relevanceFill}
                        style={{ width: `${pct}%`, background: scoreColor }}
                      />
                    </div>
                    {src.excerpt && (
                      <p className={styles.sourceExcerpt}>{src.excerpt}</p>
                    )}
                  </li>
                );
              })}
            </ul>
          </details>
        )}

        {/* ── Triggered rules (neuro-symbolic layer) ─── */}
        {message.triggered_rules && message.triggered_rules.length > 0 && (
          <TriggeredRulesPanel rules={message.triggered_rules} />
        )}

        {/* ── Reasoning steps ──────────────────────────── */}
        {message.reasoning_steps && message.reasoning_steps.length > 0 && (
          <ReasoningStepsPanel steps={message.reasoning_steps} />
        )}

        <div className={styles.meta}>
          <span>
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          {message.tokens_used !== undefined && (
            <span className={styles.tokens}>{message.tokens_used} tokens</span>
          )}
          {!isUser && (
            <button
              className={styles.copyBtn}
              onClick={handleCopy}
              title={copied ? "Copied!" : "Copy response"}
              aria-label="Copy response"
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
              {copied ? "Copied" : "Copy"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
      <path d="M12 12c2.7 0 5-2.3 5-5s-2.3-5-5-5-5 2.3-5 5 2.3 5 5 5zm0 2c-3.3 0-10 1.7-10 5v1h20v-1c0-3.3-6.7-5-10-5z" />
    </svg>
  );
}

function AIIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <path d="M12 3v18M5 6h14M3 10l4 6M17 10l4 6M3 16h8M13 16h8" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="11" height="11">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="10" height="10">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="11" height="11">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="11" height="11">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

// ── Neuro-symbolic panels ─────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  HIGH:   "rgba(239,68,68,0.9)",
  MEDIUM: "rgba(245,158,11,0.9)",
  LOW:    "rgba(59,130,246,0.85)",
};

const SEVERITY_DIM: Record<string, string> = {
  HIGH:   "rgba(239,68,68,0.08)",
  MEDIUM: "rgba(245,158,11,0.08)",
  LOW:    "rgba(59,130,246,0.08)",
};

function TriggeredRulesPanel({ rules }: { rules: TriggeredRule[] }) {
  const hasHigh   = rules.some((r) => r.severity === "HIGH");
  const hasMedium = rules.some((r) => r.severity === "MEDIUM");
  const accent    = hasHigh ? SEVERITY_COLORS.HIGH : hasMedium ? SEVERITY_COLORS.MEDIUM : SEVERITY_COLORS.LOW;

  return (
    <details className={styles.rulesPanel} style={{ "--rule-accent": accent } as React.CSSProperties}>
      <summary className={styles.rulesSummary}>
        <ShieldIcon color={accent} />
        <span style={{ color: accent }}>
          {rules.length} symbolic rule{rules.length !== 1 ? "s" : ""} triggered
        </span>
      </summary>
      <div className={styles.rulesList}>
        {rules.map((rule) => {
          const col = SEVERITY_COLORS[rule.severity] ?? SEVERITY_COLORS.info;
          const bg  = SEVERITY_DIM[rule.severity]    ?? SEVERITY_DIM.info;
          return (
            <div key={rule.rule_id} className={styles.ruleCard}
                 style={{ borderColor: col, background: bg }}>
              <div className={styles.ruleHeader}>
                <span className={styles.ruleName}>{rule.rule_name}</span>
                <span className={styles.ruleSeverity} style={{ color: col, borderColor: col }}>
                  {rule.severity.toLowerCase()}
                </span>
              </div>
              <p className={styles.ruleText}>{rule.explanation}</p>
              {rule.recommended_action && (
                <p className={styles.ruleAction}>
                  <strong>Action:</strong> {rule.recommended_action}
                </p>
              )}
              {rule.legal_reference && (
                <p className={styles.ruleCite}>{rule.legal_reference}</p>
              )}
            </div>
          );
        })}
      </div>
    </details>
  );
}

function ReasoningStepsPanel({ steps }: { steps: ReasoningStep[] }) {
  return (
    <details className={styles.reasoningPanel}>
      <summary className={styles.reasoningSummary}>
        <ThinkIcon />
        Lawyer-mode reasoning ({steps.length} steps)
      </summary>
      <ol className={styles.stepsList}>
        {steps.map((s) => (
          <li key={s.step} className={styles.step}>
            <div className={styles.stepNum}>{s.step}</div>
            <div className={styles.stepBody}>
              <strong className={styles.stepTitle}>{s.title}</strong>
              <p className={styles.stepDetail}>{s.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </details>
  );
}

function ShieldIcon({ color }: { color: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="11" height="11" style={{flexShrink:0}}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function ThinkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="11" height="11" style={{flexShrink:0}}>
      <circle cx="12" cy="12" r="10"/>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}
