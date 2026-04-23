import { useState } from "react";
import { api } from "../api/client";
import type { AnalyzeResponse } from "../types";
import styles from "./AnalyzerPage.module.css";

export function AnalyzerPage() {
  const [text, setText] = useState("");
  const [docType, setDocType] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.analyzeDocument({ text: text.trim(), document_type: docType });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          <AnalyzeIcon />
          Contract &amp; Document Analyzer
        </h1>
        <p className={styles.subtitle}>
          Paste any legal text — contract, court order, notice, statute — and get structured
          analysis with risk flags, obligations, and applicable Indian laws.
        </p>
      </div>

      <div className={styles.inputSection}>
        <div className={styles.row}>
          <label className={styles.label}>Document Type (optional hint)</label>
          <select
            className={styles.select}
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
          >
            <option value="auto">Auto-detect</option>
            <option value="contract">Contract / Agreement</option>
            <option value="judgment">Court Judgment / Order</option>
            <option value="notice">Legal Notice</option>
            <option value="statute">Statute / Act Excerpt</option>
            <option value="affidavit">Affidavit</option>
            <option value="nda">NDA</option>
          </select>
        </div>

        <textarea
          className={styles.textarea}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste your legal text here…&#10;&#10;Example: Copy a contract clause, court order, or any legal document text for analysis."
          rows={14}
        />

        <div className={styles.inputFooter}>
          <span className={styles.charCount}>{text.length.toLocaleString()} characters</span>
          <button
            className={styles.analyzeBtn}
            onClick={analyze}
            disabled={loading || text.trim().length < 20}
          >
            {loading ? <Spinner /> : <AnalyzeIcon />}
            {loading ? "Analyzing…" : "Analyze Document"}
          </button>
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {result && (
        <div className={styles.results}>
          <div className={styles.resultHeader}>
            <div className={styles.docTypeBadge}>{result.document_type}</div>
            <h2 className={styles.summaryTitle}>Analysis Complete</h2>
          </div>

          <div className={styles.summary}>{result.summary}</div>

          <div className={styles.grid}>
            {result.key_clauses.length > 0 && (
              <Section title="Key Clauses" icon="📋" items={result.key_clauses} color="blue" />
            )}
            {result.obligations.length > 0 && (
              <Section title="Obligations" icon="⚖️" items={result.obligations} color="purple" />
            )}
            {result.risk_flags.length > 0 && (
              <Section title="Risk Flags" icon="⚠️" items={result.risk_flags} color="red" />
            )}
            {result.missing_clauses.length > 0 && (
              <Section title="Missing Clauses" icon="❌" items={result.missing_clauses} color="orange" />
            )}
            {result.applicable_laws.length > 0 && (
              <Section title="Applicable Laws" icon="📖" items={result.applicable_laws} color="green" />
            )}
          </div>

          {result.jurisdiction_notes && (
            <div className={styles.jurisdictionCard}>
              <div className={styles.sectionHeader}>
                <span>🏛️</span>
                <strong>Jurisdiction Notes</strong>
              </div>
              <p className={styles.jurisdictionText}>{result.jurisdiction_notes}</p>
            </div>
          )}

          <details className={styles.rawDetails}>
            <summary className={styles.rawSummary}>View raw AI analysis</summary>
            <pre className={styles.rawText}>{result.raw_analysis}</pre>
          </details>
        </div>
      )}
    </div>
  );
}

function Section({
  title,
  icon,
  items,
  color,
}: {
  title: string;
  icon: string;
  items: string[];
  color: string;
}) {
  return (
    <div className={`${styles.section} ${styles[color]}`}>
      <div className={styles.sectionHeader}>
        <span>{icon}</span>
        <strong>{title}</strong>
        <span className={styles.count}>{items.length}</span>
      </div>
      <ul className={styles.itemList}>
        {items.map((item, i) => (
          <li key={i} className={styles.item}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AnalyzeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
         strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="11" y1="8" x2="11" y2="14" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="16" height="16"
         style={{ animation: "spin 1s linear infinite" }}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}
