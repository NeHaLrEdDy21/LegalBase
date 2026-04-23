import { useState, useRef } from "react";
import { api } from "../api/client";
import type { SimilarResult } from "../types";
import styles from "./SearchPage.module.css";

const CATEGORY_COLORS: Record<string, string> = {
  CONSTITUTIONAL: "#4a6fa5",
  CRIMINAL: "#c0392b",
  CONTRACT: "#27ae60",
  TORT: "#e67e22",
  PROPERTY: "#8e44ad",
  COMPANY: "#2980b9",
  EVIDENCE: "#16a085",
  PROCEDURE: "#7f8c8d",
  WRIT: "#d35400",
  CYBER: "#1abc9c",
  IP: "#9b59b6",
  ENVIRONMENT: "#2ecc71",
  FAMILY: "#e91e63",
  EMPLOYMENT: "#ff9800",
  BANKING: "#3498db",
  CONSUMER: "#f39c12",
  RTI: "#1565c0",
};

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SimilarResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const search = async () => {
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResults([]);
    setSearched(false);
    try {
      const res = await api.findSimilar(query.trim(), 10);
      setResults(res.results);
      setSearched(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") search();
  };

  const SUGGESTIONS = [
    "right to privacy fundamental right",
    "murder punishment life imprisonment",
    "contract breach compensation",
    "cyber crime penalty IT Act",
    "bail non-bailable offence",
    "habeas corpus writ",
    "copyright infringement",
    "consumer deficiency refund",
  ];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          <SearchIcon />
          Legal Knowledge Search
        </h1>
        <p className={styles.subtitle}>
          Semantic search over {582} vectors — Indian Constitution, IPC/BNS, Contract Act,
          Evidence Act, Companies Act, IT Act, and more.
        </p>
      </div>

      <div className={styles.searchBox}>
        <input
          ref={inputRef}
          className={styles.searchInput}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKey}
          placeholder="Search Indian law… e.g. 'right to privacy', 'bail conditions', 'copyright infringement'"
          autoFocus
        />
        <button
          className={styles.searchBtn}
          onClick={search}
          disabled={loading || query.trim().length < 3}
        >
          {loading ? <Spinner /> : <SearchIcon />}
        </button>
      </div>

      {!searched && !loading && (
        <div className={styles.suggestions}>
          <span className={styles.suggestionsLabel}>Try:</span>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className={styles.suggestionChip}
              onClick={() => { setQuery(s); setTimeout(search, 50); }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}

      {searched && results.length === 0 && !loading && (
        <div className={styles.noResults}>No results found. Try different keywords.</div>
      )}

      {results.length > 0 && (
        <div className={styles.results}>
          <div className={styles.resultsHeader}>
            <span className={styles.resultCount}>{results.length} results</span>
            <span className={styles.queryEcho}>for "{query}"</span>
          </div>
          {results.map((r, i) => (
            <div key={i} className={styles.card}>
              <div className={styles.cardHeader}>
                <div
                  className={styles.categoryBadge}
                  style={{ background: `${CATEGORY_COLORS[r.category] ?? "#4a5a6a"}22`,
                           borderColor: `${CATEGORY_COLORS[r.category] ?? "#4a5a6a"}66`,
                           color: CATEGORY_COLORS[r.category] ?? "#8a9bb0" }}
                >
                  {r.category}
                </div>
                <span className={styles.jurisdiction}>{r.jurisdiction}</span>
                <div className={styles.scoreBar}>
                  <div
                    className={styles.scoreFill}
                    style={{ width: `${Math.round(r.score * 100)}%` }}
                  />
                  <span className={styles.scoreText}>{Math.round(r.score * 100)}%</span>
                </div>
              </div>
              <h3 className={styles.cardTitle}>{r.title}</h3>
              <p className={styles.excerpt}>{r.excerpt}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
         strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="18" height="18"
         style={{ animation: "spin 1s linear infinite" }}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}
