import { useState } from "react";
import { api } from "../api/client";
import type { GenerateDocResponse } from "../types";
import styles from "./DocGeneratorPage.module.css";

const DOC_TYPES = [
  { value: "nda", label: "Non-Disclosure Agreement (NDA)" },
  { value: "rent_agreement", label: "Rent / Lease Agreement" },
  { value: "employment_agreement", label: "Employment Agreement" },
  { value: "legal_notice", label: "Legal Notice" },
  { value: "affidavit", label: "Affidavit" },
  { value: "power_of_attorney", label: "Power of Attorney" },
  { value: "sale_agreement", label: "Sale / Purchase Agreement" },
  { value: "loan_agreement", label: "Loan Agreement" },
  { value: "partnership_deed", label: "Partnership Deed" },
  { value: "demand_notice", label: "Demand Notice" },
];

const TERM_HINTS: Record<string, { key: string; placeholder: string }[]> = {
  nda: [
    { key: "confidentiality_period", placeholder: "e.g. 2 years" },
    { key: "purpose", placeholder: "e.g. evaluation of business opportunity" },
    { key: "governing_state", placeholder: "e.g. Maharashtra" },
  ],
  rent_agreement: [
    { key: "property_address", placeholder: "Full address" },
    { key: "monthly_rent", placeholder: "e.g. Rs. 25,000" },
    { key: "security_deposit", placeholder: "e.g. Rs. 75,000 (3 months)" },
    { key: "lease_term", placeholder: "e.g. 11 months" },
    { key: "commencement_date", placeholder: "e.g. 1st May 2025" },
  ],
  employment_agreement: [
    { key: "designation", placeholder: "e.g. Software Engineer" },
    { key: "ctc", placeholder: "e.g. Rs. 8,00,000 per annum" },
    { key: "notice_period", placeholder: "e.g. 60 days" },
    { key: "joining_date", placeholder: "e.g. 15th April 2025" },
    { key: "work_location", placeholder: "e.g. Hyderabad, Telangana" },
  ],
  legal_notice: [
    { key: "cause_of_action", placeholder: "e.g. non-payment of dues" },
    { key: "amount_claimed", placeholder: "e.g. Rs. 5,00,000" },
    { key: "reply_period", placeholder: "e.g. 15 days" },
  ],
  loan_agreement: [
    { key: "loan_amount", placeholder: "e.g. Rs. 10,00,000" },
    { key: "interest_rate", placeholder: "e.g. 12% per annum" },
    { key: "repayment_period", placeholder: "e.g. 24 months" },
    { key: "emi_amount", placeholder: "e.g. Rs. 47,073 per month" },
  ],
};

export function DocGeneratorPage() {
  const [docType, setDocType] = useState("nda");
  const [partyA, setPartyA] = useState("");
  const [partyB, setPartyB] = useState("");
  const [jurisdiction, setJurisdiction] = useState("India");
  const [additionalContext, setAdditionalContext] = useState("");
  const [keyTerms, setKeyTerms] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateDocResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const termHints = TERM_HINTS[docType] ?? [];

  const generate = async () => {
    if (!partyA.trim() || !partyB.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const filteredTerms = Object.fromEntries(
        Object.entries(keyTerms).filter(([, v]) => v.trim())
      );
      const res = await api.generateDoc({
        document_type: docType,
        party_a: partyA.trim(),
        party_b: partyB.trim(),
        jurisdiction,
        additional_context: additionalContext,
        key_terms: filteredTerms,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadTxt = () => {
    if (!result) return;
    const blob = new Blob([result.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.title.replace(/[^a-z0-9]/gi, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          <DocIcon />
          Legal Document Generator
        </h1>
        <p className={styles.subtitle}>
          Generate standard Indian legal documents — NDAs, rent agreements, employment contracts,
          legal notices, and more — powered by AI with correct statutory references.
        </p>
      </div>

      <div className={styles.form}>
        <div className={styles.formGroup}>
          <label className={styles.label}>Document Type</label>
          <div className={styles.docTypeGrid}>
            {DOC_TYPES.map((dt) => (
              <button
                key={dt.value}
                className={`${styles.docTypeBtn} ${docType === dt.value ? styles.docTypeActive : ""}`}
                onClick={() => { setDocType(dt.value); setKeyTerms({}); }}
              >
                {dt.label}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.row2}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Party A (First Party)</label>
            <input
              className={styles.input}
              value={partyA}
              onChange={(e) => setPartyA(e.target.value)}
              placeholder="Full name, address, designation…"
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Party B (Second Party)</label>
            <input
              className={styles.input}
              value={partyB}
              onChange={(e) => setPartyB(e.target.value)}
              placeholder="Full name, address, designation…"
            />
          </div>
        </div>

        {termHints.length > 0 && (
          <div className={styles.formGroup}>
            <label className={styles.label}>Key Terms</label>
            <div className={styles.termsGrid}>
              {termHints.map((hint) => (
                <div key={hint.key} className={styles.termRow}>
                  <span className={styles.termKey}>{hint.key.replace(/_/g, " ")}</span>
                  <input
                    className={styles.termInput}
                    value={keyTerms[hint.key] ?? ""}
                    onChange={(e) =>
                      setKeyTerms((prev) => ({ ...prev, [hint.key]: e.target.value }))
                    }
                    placeholder={hint.placeholder}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <div className={styles.row2}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Governing Jurisdiction</label>
            <input
              className={styles.input}
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              placeholder="India / Maharashtra / Telangana…"
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Additional Instructions (optional)</label>
            <input
              className={styles.input}
              value={additionalContext}
              onChange={(e) => setAdditionalContext(e.target.value)}
              placeholder="Add specific clauses or requirements…"
            />
          </div>
        </div>

        <div className={styles.generateRow}>
          <button
            className={styles.generateBtn}
            onClick={generate}
            disabled={loading || !partyA.trim() || !partyB.trim()}
          >
            {loading ? <Spinner /> : <DocIcon />}
            {loading ? "Generating…" : "Generate Document"}
          </button>
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {result && (
        <div className={styles.resultSection}>
          <div className={styles.resultHeader}>
            <h2 className={styles.resultTitle}>{result.title}</h2>
            <div className={styles.resultActions}>
              <button className={styles.actionBtn} onClick={copyToClipboard}>
                {copied ? "✓ Copied" : "Copy"}
              </button>
              <button className={styles.actionBtn} onClick={downloadTxt}>
                Download .txt
              </button>
            </div>
          </div>

          <div className={styles.lawTags}>
            {result.applicable_laws.map((law, i) => (
              <span key={i} className={styles.lawTag}>{law}</span>
            ))}
          </div>

          <pre className={styles.docContent}>{result.content}</pre>

          <div className={styles.disclaimer}>
            <span className={styles.disclaimerIcon}>⚠️</span>
            {result.notes}
          </div>
        </div>
      )}
    </div>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
         strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
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
