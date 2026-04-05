import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { KnowledgeBaseDocument } from "../types";
import styles from "./KnowledgeBasePage.module.css";

interface Props {
  onChunkCountChange?: (n: number) => void;
}

export function KnowledgeBasePage({ onChunkCountChange }: Props) {
  const [docs, setDocs] = useState<KnowledgeBaseDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.listDocuments();
      setDocs(data);
      const total = data.reduce((s, d) => s + d.chunk_count, 0);
      onChunkCountChange?.(total);
    } catch {
      setError("Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }, [onChunkCountChange]);

  useEffect(() => { load(); }, [load]);

  const flash = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3500);
  };

  const handleDelete = async (doc: KnowledgeBaseDocument) => {
    if (!confirm(`Remove "${doc.filename}" and all its ${doc.chunk_count} chunk(s) from the knowledge base?`)) return;
    setDeletingId(doc.document_id);
    setError(null);
    try {
      await api.deleteDocument(doc.document_id);
      flash(`Removed "${doc.filename}".`);
      await load();
    } catch {
      setError(`Failed to delete "${doc.filename}".`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleFile = async (file: File) => {
    const MAX = 20 * 1024 * 1024;
    if (file.size > MAX) { setError("File exceeds 20 MB limit."); return; }
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx", "txt"].includes(ext ?? "")) {
      setError("Only PDF, DOCX, and TXT files are supported.");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const r = await api.ingestFile(file);
      flash(`Indexed "${r.filename}" — ${r.total_chunks} chunk(s) added.`);
      await load();
    } catch {
      setError("Upload failed. Check the file format and try again.");
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const totalChunks = docs.reduce((s, d) => s + d.chunk_count, 0);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <DatabaseIcon />
          <div>
            <h1 className={styles.title}>Knowledge Base</h1>
            <p className={styles.subtitle}>
              Documents are embedded and persisted — available to all future queries.
            </p>
          </div>
        </div>
        <div className={styles.stats}>
          <Stat label="Documents" value={docs.length} />
          <Stat label="Chunks" value={totalChunks} accent />
        </div>
      </header>

      {/* ── Upload zone ──────────────────────────────────────────────── */}
      <div
        className={`${styles.dropzone} ${dragOver ? styles.dragOver : ""} ${uploading ? styles.uploading : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => !uploading && document.getElementById("kb-file-input")?.click()}
      >
        <input
          id="kb-file-input"
          type="file"
          accept=".pdf,.docx,.txt"
          className={styles.hiddenInput}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }}
        />
        {uploading ? (
          <>
            <div className={styles.spinner} />
            <span className={styles.dropzoneText}>Indexing document…</span>
          </>
        ) : (
          <>
            <UploadIcon />
            <span className={styles.dropzoneText}>
              Drop a file or <strong>click to browse</strong>
            </span>
            <span className={styles.dropzoneHint}>PDF · DOCX · TXT — max 20 MB</span>
          </>
        )}
      </div>

      {/* ── Feedback ─────────────────────────────────────────────────── */}
      {successMsg && (
        <div className={styles.success}><CheckIcon />{successMsg}</div>
      )}
      {error && (
        <div className={styles.error}><ErrorIcon />{error}</div>
      )}

      {/* ── Document list ─────────────────────────────────────────────── */}
      <section className={styles.listSection}>
        <h2 className={styles.listTitle}>Indexed Documents</h2>
        {loading ? (
          <div className={styles.emptyState}><div className={styles.spinner} /></div>
        ) : docs.length === 0 ? (
          <div className={styles.emptyState}>
            <EmptyIcon />
            <p>No documents yet. Upload one above to get started.</p>
          </div>
        ) : (
          <ul className={styles.list}>
            {docs.map((doc) => (
              <li key={doc.document_id} className={styles.docRow}>
                <FileIcon filename={doc.filename} />
                <div className={styles.docInfo}>
                  <span className={styles.docName}>{doc.filename}</span>
                  <span className={styles.docMeta}>
                    {doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""}
                    {doc.extra?.category ? ` · ${doc.extra.category}` : ""}
                  </span>
                </div>
                <span className={styles.docId}>{doc.document_id.slice(0, 8)}…</span>
                <button
                  className={styles.deleteBtn}
                  onClick={() => handleDelete(doc)}
                  disabled={deletingId === doc.document_id}
                  title="Remove from knowledge base"
                >
                  {deletingId === doc.document_id ? (
                    <div className={styles.spinnerSm} />
                  ) : (
                    <TrashIcon />
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Stat({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={styles.stat}>
      <span className={`${styles.statValue} ${accent ? styles.accentValue : ""}`}>{value}</span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}

function FileIcon({ filename }: { filename: string }) {
  const ext = filename.split(".").pop()?.toLowerCase();
  const color = ext === "pdf" ? "#f87171" : ext === "docx" ? "#60a5fa" : "#a3e635";
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.6"
         strokeLinecap="round" strokeLinejoin="round" width="18" height="18" style={{ flexShrink: 0 }}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" /><line x1="8" y1="17" x2="16" y2="17" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
         strokeLinecap="round" strokeLinejoin="round" width="32" height="32">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
         strokeLinecap="round" strokeLinejoin="round" width="22" height="22">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6M9 6V4h6v2" />
    </svg>
  );
}

function EmptyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2"
         strokeLinecap="round" strokeLinejoin="round" width="40" height="40" style={{ opacity: 0.3 }}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
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
