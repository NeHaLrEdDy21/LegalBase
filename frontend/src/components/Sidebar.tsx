import styles from "./Sidebar.module.css";

export type AppView = "chat" | "knowledge-base" | "rules";

interface Props {
  firstName: string;
  email: string;
  onSignOut: () => void;
  sessionId: string | null;
  onNewChat: () => void;
  view: AppView;
  onViewChange: (v: AppView) => void;
  chunkCount: number | null;
}

export function Sidebar({ firstName, email, onSignOut, sessionId, onNewChat, view, onViewChange, chunkCount }: Props) {

  return (
    <aside className={styles.sidebar}>
      {/* ── Logo ───────────────────────────────────────────── */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}><ScalesIcon /></div>
        <div className={styles.logoText}>
          <span className={styles.logoName}>LegalMind</span>
          <span className={styles.logoTagline}>Neuro-Symbolic AI</span>
        </div>
      </div>

      {/* ── New chat ────────────────────────────────────────── */}
      <button className={styles.newChat} onClick={() => { onNewChat(); onViewChange("chat"); }}>
        <PlusIcon />
        New conversation
      </button>

      {sessionId && view === "chat" && (
        <div className={styles.sessionTag}>
          <span className={styles.dot} />
          <span>Session active</span>
          <span className={styles.sessionId}>{sessionId.slice(0, 8)}…</span>
        </div>
      )}

      <div className={styles.divider} />

      {/* ── View nav ────────────────────────────────────────── */}
      <nav className={styles.nav}>
        <NavItem
          active={view === "chat"}
          onClick={() => onViewChange("chat")}
          icon={<ChatIcon />}
          label="Chat"
        />
        <NavItem
          active={view === "knowledge-base"}
          onClick={() => onViewChange("knowledge-base")}
          icon={<DatabaseIcon />}
          label="Knowledge Base"
          badge={chunkCount ?? undefined}
        />
        <NavItem
          active={view === "rules"}
          onClick={() => onViewChange("rules")}
          icon={<ShieldIcon />}
          label="Symbolic Rules"
        />
      </nav>

      {/* ── Footer user row ─────────────────────────────────── */}
      <div className={styles.footer}>
        <div className={styles.userRow}>
          <div className={styles.avatar}>
            {(firstName?.[0] ?? email?.[0] ?? "U").toUpperCase()}
          </div>
          <div className={styles.userInfo}>
            <span className={styles.userName}>{firstName || "User"}</span>
            <span className={styles.userEmail}>{email}</span>
          </div>
          <button className={styles.signOutBtn} onClick={onSignOut} title="Sign out" aria-label="Sign out">
            <SignOutIcon />
          </button>
        </div>
      </div>
    </aside>
  );
}

function NavItem({
  active, onClick, icon, label, badge,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  badge?: number;
}) {
  return (
    <button className={`${styles.navItem} ${active ? styles.navActive : ""}`} onClick={onClick}>
      <span className={styles.navIcon}>{icon}</span>
      <span className={styles.navLabel}>{label}</span>
      {badge !== undefined && (
        <span className={styles.navBadge}>{badge}</span>
      )}
    </button>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function ScalesIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
         strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <path d="M12 3v18M5 6h14M3 10l4 6M17 10l4 6M3 16h8M13 16h8" />
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

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
         strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
         strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75"
         strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function SignOutIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}
