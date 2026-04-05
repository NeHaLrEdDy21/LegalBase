import styles from "./TypingIndicator.module.css";

export function TypingIndicator() {
  return (
    <div className={styles.wrapper}>
      <div className={styles.avatar}>
        <AIIcon />
      </div>
      <div className={styles.bubble}>
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.label}>Researching…</span>
      </div>
    </div>
  );
}

function AIIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <path d="M12 3v18M5 6h14M3 10l4 6M17 10l4 6M3 16h8M13 16h8" />
    </svg>
  );
}
