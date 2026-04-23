import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { Rule, RuleCreate } from "../types";
import styles from "./RulesPage.module.css";

const EMPTY_FORM: RuleCreate = {
  id: "",
  name: "",
  trigger_keywords: [],
  condition: "keyword_match",
  pattern: "",
  consequence: "",
  recommended_action: "",
  severity: "MEDIUM",
  legal_reference: "",
};

export function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<RuleCreate>(EMPTY_FORM);
  const [keywordsInput, setKeywordsInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"ALL" | "HIGH" | "MEDIUM" | "LOW">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await api.listRules();
      setRules(data);
    } catch {
      setError("Failed to load rules.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const flash = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3500);
  };

  const handleDelete = async (rule: Rule) => {
    if (!confirm(`Delete rule "${rule.name}" (${rule.id})?`)) return;
    setDeletingId(rule.id);
    setError(null);
    try {
      await api.deleteRule(rule.id);
      flash(`Deleted "${rule.name}".`);
      await load();
    } catch {
      setError(`Failed to delete "${rule.name}".`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!form.id.trim()) { setError("Rule ID is required."); return; }
    if (!form.name.trim()) { setError("Rule name is required."); return; }
    if (!form.consequence.trim()) { setError("Consequence is required."); return; }
    if (!form.recommended_action.trim()) { setError("Recommended action is required."); return; }
    if (form.condition === "keyword_match" && keywordsInput.trim() === "") {
      setError("Provide at least one trigger keyword for keyword_match rules."); return;
    }
    if (form.condition === "regex_match" && !form.pattern.trim()) {
      setError("Provide a regex pattern for regex_match rules."); return;
    }

    setSaving(true);
    try {
      const keywords = keywordsInput
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean);
      await api.addRule({ ...form, id: form.id.trim().toUpperCase(), trigger_keywords: keywords });
      flash(`Rule "${form.name}" added.`);
      setForm(EMPTY_FORM);
      setKeywordsInput("");
      setShowForm(false);
      await load();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to save rule.");
    } finally {
      setSaving(false);
    }
  };

  const filtered = rules.filter((r) => {
    const severityMatch = filter === "ALL" || r.severity === filter;
    const searchMatch = searchQuery === "" ||
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.trigger_keywords.some(k => k.toLowerCase().includes(searchQuery.toLowerCase()));
    return severityMatch && searchMatch;
  });

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <RulesIcon />
          <div>
            <h1 className={styles.title}>Symbolic Constraints</h1>
            <p className={styles.subtitle}>
              Rules evaluated against every response — trigger legal flags and recommended actions.
            </p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search rules by name, ID, or keyword…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <div className={styles.filterGroup}>
            {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((s) => (
              <button
                key={s}
                className={`${styles.filterBtn} ${filter === s ? styles.filterActive : ""} ${s !== "ALL" ? styles[`sev${s}`] : ""}`}
                onClick={() => setFilter(s)}
              >
                {s === "ALL" ? `All` : `${s}`}
              </button>
            ))}
          </div>
          <button className={styles.addBtn} onClick={() => { setShowForm((v) => !v); setError(null); }}>
            <PlusIcon />
            {showForm ? "Cancel" : "Add"}
          </button>
        </div>
      </header>

      {/* ── Feedback ──────────────────────────────────────────────────── */}
      {successMsg && <div className={styles.success}><CheckIcon />{successMsg}</div>}
      {error && <div className={styles.error}><ErrorIcon />{error}</div>}

      {/* ── Add rule form ─────────────────────────────────────────────── */}
      {showForm && (
        <form className={styles.form} onSubmit={handleSubmit}>
          <h2 className={styles.formTitle}>New Symbolic Rule</h2>

          <div className={styles.formGrid}>
            <Field label="Rule ID *" hint="e.g. TORT_002">
              <input
                className={styles.input}
                value={form.id}
                onChange={(e) => setForm((f) => ({ ...f, id: e.target.value }))}
                placeholder="CONTRACT_005"
              />
            </Field>
            <Field label="Severity *">
              <select
                className={styles.select}
                value={form.severity}
                onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value as Rule["severity"] }))}
              >
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </Field>
          </div>

          <Field label="Rule Name *">
            <input
              className={styles.input}
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Penalty Clause — Unconscionability"
            />
          </Field>

          <Field label="Condition Type *">
            <select
              className={styles.select}
              value={form.condition}
              onChange={(e) => setForm((f) => ({ ...f, condition: e.target.value as Rule["condition"] }))}
            >
              <option value="keyword_match">Keyword Match</option>
              <option value="regex_match">Regex Match</option>
            </select>
          </Field>

          {form.condition === "keyword_match" ? (
            <Field label="Trigger Keywords *" hint="Comma-separated">
              <input
                className={styles.input}
                value={keywordsInput}
                onChange={(e) => setKeywordsInput(e.target.value)}
                placeholder="penalty clause, liquidated damages, excessive fine"
              />
            </Field>
          ) : (
            <Field label="Regex Pattern *" hint="Python re.search syntax">
              <input
                className={styles.input}
                value={form.pattern}
                onChange={(e) => setForm((f) => ({ ...f, pattern: e.target.value }))}
                placeholder="penalty\s+clause|liquidated\s+damages"
              />
            </Field>
          )}

          <Field label="Legal Consequence *">
            <textarea
              className={styles.textarea}
              value={form.consequence}
              onChange={(e) => setForm((f) => ({ ...f, consequence: e.target.value }))}
              placeholder="A penalty clause that is disproportionate to the legitimate interest is unenforceable."
              rows={2}
            />
          </Field>

          <Field label="Recommended Action *">
            <textarea
              className={styles.textarea}
              value={form.recommended_action}
              onChange={(e) => setForm((f) => ({ ...f, recommended_action: e.target.value }))}
              placeholder="Advise client to negotiate a genuine pre-estimate of loss clause."
              rows={2}
            />
          </Field>

          <Field label="Legal Reference">
            <input
              className={styles.input}
              value={form.legal_reference}
              onChange={(e) => setForm((f) => ({ ...f, legal_reference: e.target.value }))}
              placeholder="Cavendish Square v Makdessi [2015] UKSC 67"
            />
          </Field>

          <div className={styles.formActions}>
            <button type="submit" className={styles.saveBtn} disabled={saving}>
              {saving ? <div className={styles.spinnerSm} /> : <CheckIcon />}
              {saving ? "Saving…" : "Save rule"}
            </button>
          </div>
        </form>
      )}

      {/* ── Rules list ────────────────────────────────────────────────── */}
      <section className={styles.listSection}>
        {loading ? (
          <div className={styles.emptyState}><div className={styles.spinner} /></div>
        ) : filtered.length === 0 ? (
          <div className={styles.emptyState}>
            <RulesEmptyIcon />
            <p>{filter === "ALL" ? "No rules yet. Add one above." : `No ${filter} severity rules.`}</p>
          </div>
        ) : (
          <ul className={styles.list}>
            {filtered.map((rule) => {
              const expanded = expandedId === rule.id;
              return (
                <li key={rule.id} className={styles.ruleCard}>
                  <div className={styles.ruleHeader} onClick={() => setExpandedId(expanded ? null : rule.id)}>
                    <span className={`${styles.badge} ${styles[`sev${rule.severity}`]}`}>{rule.severity}</span>
                    <div className={styles.ruleTitle}>
                      <span className={styles.ruleName}>{rule.name}</span>
                      <span className={styles.ruleId}>{rule.id}</span>
                    </div>
                    <div className={styles.ruleActions}>
                      <button
                        className={styles.deleteBtn}
                        onClick={(e) => { e.stopPropagation(); handleDelete(rule); }}
                        disabled={deletingId === rule.id}
                        title="Delete rule"
                      >
                        {deletingId === rule.id ? <div className={styles.spinnerSm} /> : <TrashIcon />}
                      </button>
                      <ChevronIcon expanded={expanded} />
                    </div>
                  </div>

                  {expanded && (
                    <div className={styles.ruleBody}>
                      <Detail label="Condition">
                        <span className={styles.condBadge}>{rule.condition}</span>
                      </Detail>
                      {rule.condition === "keyword_match" && rule.trigger_keywords.length > 0 && (
                        <Detail label="Keywords">
                          <div className={styles.keywords}>
                            {rule.trigger_keywords.map((kw) => (
                              <span key={kw} className={styles.kw}>{kw}</span>
                            ))}
                          </div>
                        </Detail>
                      )}
                      {rule.condition === "regex_match" && rule.pattern && (
                        <Detail label="Pattern">
                          <code className={styles.code}>{rule.pattern}</code>
                        </Detail>
                      )}
                      <Detail label="Consequence">{rule.consequence}</Detail>
                      <Detail label="Recommended Action">{rule.recommended_action}</Detail>
                      {rule.legal_reference && (
                        <Detail label="Legal Reference">
                          <em className={styles.cite}>{rule.legal_reference}</em>
                        </Detail>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className={styles.field}>
      <label className={styles.label}>
        {label}
        {hint && <span className={styles.hint}> — {hint}</span>}
      </label>
      {children}
    </div>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className={styles.detail}>
      <span className={styles.detailLabel}>{label}</span>
      <span className={styles.detailValue}>{children}</span>
    </div>
  );
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="14" height="14"
         style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.2s ease", flexShrink: 0, opacity: 0.5 }}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function RulesIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
         strokeLinecap="round" strokeLinejoin="round" width="22" height="22">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
         strokeLinecap="round" strokeLinejoin="round" width="13" height="13">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="13" height="13">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6M14 11v6M9 6V4h6v2" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
         strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function RulesEmptyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2"
         strokeLinecap="round" strokeLinejoin="round" width="40" height="40" style={{ opacity: 0.3 }}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}
