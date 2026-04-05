import { useState, useRef } from "react";
import { api } from "../api/client";
import type { IngestResponse } from "../types";
import styles from "./DocumentUpload.module.css";

const ACCEPTED = ".txt,.pdf,.docx";
const MAX_MB = 20;

interface Props {
  onSuccess?: (meta: IngestResponse) => void;
}

export function DocumentUpload({ onSuccess }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = async (file: File) => {
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File exceeds ${MAX_MB} MB limit.`);
      return;
    }
    setIsUploading(true);
    setError(null);
    setResult(null);
    try {
      const meta = await api.ingestFile(file);
      setResult(meta);
      onSuccess?.(meta);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed.";
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) upload(file);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) upload(file);
    e.target.value = "";
  };

  return (
    <div className={styles.wrapper}>
      <div
        className={`${styles.dropzone} ${isDragging ? styles.dragging : ""} ${isUploading ? styles.uploading : ""}`}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        role="button"
        aria-label="Upload document"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED}
          className={styles.hidden}
          onChange={onFileChange}
        />
        {isUploading ? (
          <span className={styles.uploading}>Uploading…</span>
        ) : (
          <>
            <UploadIcon />
            <span>Drop a file or click to upload</span>
            <small>PDF, DOCX, TXT — max {MAX_MB} MB</small>
          </>
        )}
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {result && (
        <div className={styles.success}>
          <strong>{result.filename}</strong> ingested —{" "}
          {result.total_chunks} chunk{result.total_chunks !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}
         width="28" height="28">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  );
}
