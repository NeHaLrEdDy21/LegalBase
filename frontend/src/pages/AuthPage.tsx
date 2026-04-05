import { useState, type FormEvent } from "react";
import { SignIn, SignUp } from "@clerk/clerk-react";
import { useAuth } from "../auth/AuthContext";
import { clerkConfigured } from "../App";
import styles from "./AuthPage.module.css";

type Mode = "sign-in" | "sign-up";

export function AuthPage() {
  const [mode, setMode] = useState<Mode>("sign-in");

  return clerkConfigured
    ? <ClerkAuthView mode={mode} onModeChange={setMode} />
    : <LocalAuthView mode={mode} onModeChange={setMode} />;
}

// ── Clerk auth ───────────────────────────────────────────────────────────────

function ClerkAuthView({ mode, onModeChange }: { mode: Mode; onModeChange: (m: Mode) => void }) {
  return (
    <div className={styles.container}>
      <div className={styles.scalesWrap} aria-hidden><ScalesAmbient /></div>
      <div className={styles.grid} aria-hidden />
      <div className={styles.content}>
        <header className={styles.brand}>
          <div className={styles.emblem}><ScalesIcon /></div>
          <div>
            <h1 className={styles.title}>LegalMind</h1>
            <p className={styles.subtitle}>Neuro-Symbolic Legal Research System</p>
          </div>
        </header>

        <div className={styles.clerkWrap}>
          {mode === "sign-in"
            ? <SignIn routing="hash" afterSignInUrl="/" />
            : <SignUp routing="hash" afterSignUpUrl="/" />
          }
        </div>

        <button
          className={styles.modeToggle}
          onClick={() => onModeChange(mode === "sign-in" ? "sign-up" : "sign-in")}
          type="button"
        >
          {mode === "sign-in" ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
        </button>
        <p className={styles.legal}>LegalMind provides informational assistance only — not legal advice.</p>
      </div>
    </div>
  );
}

// ── Local auth fallback ───────────────────────────────────────────────────────

function LocalAuthView({ mode, onModeChange }: { mode: Mode; onModeChange: (m: Mode) => void }) {
  const { signIn, signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "sign-in") await signIn(email, password);
      else await signUp(email, password, firstName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.scalesWrap} aria-hidden><ScalesAmbient /></div>
      <div className={styles.grid} aria-hidden />

      <div className={styles.content}>
        <header className={styles.brand}>
          <div className={styles.emblem}><ScalesIcon /></div>
          <div>
            <h1 className={styles.title}>LegalMind</h1>
            <p className={styles.subtitle}>Neuro-Symbolic Legal Research System</p>
          </div>
        </header>

        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>
              {mode === "sign-in" ? "Welcome back" : "Create account"}
            </h2>
            <p className={styles.cardSub}>
              {mode === "sign-in"
                ? "Sign in to your LegalMind workspace"
                : "Start your legal research journey"}
            </p>
          </div>

          <form className={styles.form} onSubmit={handleSubmit} noValidate>
            {mode === "sign-up" && (
              <div className={styles.field}>
                <label className={styles.label} htmlFor="firstName">First name</label>
                <input id="firstName" type="text" className={styles.input}
                  placeholder="e.g. James" value={firstName}
                  onChange={(e) => setFirstName(e.target.value)} autoComplete="given-name" />
              </div>
            )}

            <div className={styles.field}>
              <label className={styles.label} htmlFor="email">Email address</label>
              <input id="email" type="email" className={styles.input}
                placeholder="you@example.com" value={email}
                onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="password">Password</label>
              <input id="password" type="password" className={styles.input}
                placeholder={mode === "sign-up" ? "At least 8 characters" : "••••••••"}
                value={password} onChange={(e) => setPassword(e.target.value)} required
                autoComplete={mode === "sign-in" ? "current-password" : "new-password"} />
            </div>

            {error && (
              <div className={styles.error} role="alert">
                <ErrorIcon />{error}
              </div>
            )}

            <button type="submit" className={styles.submit}
              disabled={loading || !email || !password}>
              {loading ? <Spinner /> : (mode === "sign-in" ? "Sign in" : "Create account")}
            </button>
          </form>

          <div className={styles.divider}><span>or</span></div>

          <button className={styles.modeToggle}
            onClick={() => { onModeChange(mode === "sign-in" ? "sign-up" : "sign-in"); setError(null); }}
            type="button">
            {mode === "sign-in" ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>

        <p className={styles.legal}>LegalMind provides informational assistance only — not legal advice.</p>
      </div>
    </div>
  );
}

// ── Icons & helpers ────────────────────────────────────────────────────────────

function ScalesIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
         strokeLinecap="round" strokeLinejoin="round" width="22" height="22">
      <path d="M12 3v18M5 6h14M3 10l4 6M17 10l4 6M3 16h8M13 16h8" />
    </svg>
  );
}

function ScalesAmbient() {
  return (
    <svg viewBox="0 0 200 220" fill="none" xmlns="http://www.w3.org/2000/svg"
         className={styles.scalesSvg}>
      <defs>
        <linearGradient id="sg1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#a855f7" stopOpacity="0.5"/>
          <stop offset="100%" stopColor="#c9963a" stopOpacity="0.2"/>
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2.5" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <line x1="100" y1="20" x2="100" y2="190" stroke="url(#sg1)" strokeWidth="1.5" filter="url(#glow)"/>
      <line x1="30" y1="55" x2="170" y2="55" stroke="url(#sg1)" strokeWidth="1.5" filter="url(#glow)"/>
      <line x1="50" y1="55" x2="30" y2="120" stroke="#a855f7" strokeWidth="1" strokeOpacity="0.6"/>
      <line x1="50" y1="55" x2="70" y2="120" stroke="#a855f7" strokeWidth="1" strokeOpacity="0.6"/>
      <line x1="150" y1="55" x2="130" y2="130" stroke="#c9963a" strokeWidth="1" strokeOpacity="0.6"/>
      <line x1="150" y1="55" x2="170" y2="130" stroke="#c9963a" strokeWidth="1" strokeOpacity="0.6"/>
      <path d="M20 120 Q50 128 80 120" stroke="#a855f7" strokeWidth="1.5" strokeOpacity="0.8" filter="url(#glow)"/>
      <path d="M122 134 Q150 140 178 130" stroke="#c9963a" strokeWidth="1.5" strokeOpacity="0.8" filter="url(#glow)"/>
      <path d="M80 190 L120 190 L115 200 L85 200 Z" stroke="url(#sg1)" strokeWidth="1.2" fill="none" filter="url(#glow)"/>
      <circle cx="100" cy="20" r="4" stroke="url(#sg1)" strokeWidth="1.5" fill="none" filter="url(#glow)"/>
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" width="13" height="13" style={{flexShrink:0}}>
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  );
}

function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2.5" strokeLinecap="round" className={styles.spinner}>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg>
  );
}
