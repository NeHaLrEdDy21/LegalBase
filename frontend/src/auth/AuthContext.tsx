import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

export interface AuthUser {
  id: string;
  email: string;
  firstName: string;
}

interface AuthState {
  user: AuthUser | null;
  isLoaded: boolean;
}

interface AuthContextValue extends AuthState {
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, firstName: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const SESSION_KEY = "lm_session";
const ACCOUNTS_KEY = "lm_accounts";

function getAccounts(): Record<string, { hash: string; firstName: string; id: string }> {
  try { return JSON.parse(localStorage.getItem(ACCOUNTS_KEY) ?? "{}"); }
  catch { return {}; }
}

// Simple deterministic hash (demo-only — not cryptographic)
async function hashPassword(password: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(password));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      if (raw) {
        const user: AuthUser = JSON.parse(raw);
        return { user, isLoaded: true };
      }
    } catch { /* ignore */ }
    return { user: null, isLoaded: true };
  });

  const signIn = useCallback(async (email: string, password: string) => {
    const accounts = getAccounts();
    const key = email.toLowerCase();
    const account = accounts[key];
    if (!account) throw new Error("No account found for this email.");
    const hash = await hashPassword(password);
    if (hash !== account.hash) throw new Error("Incorrect password.");
    const user: AuthUser = { id: account.id, email: key, firstName: account.firstName };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(user));
    setState({ user, isLoaded: true });
  }, []);

  const signUp = useCallback(async (email: string, password: string, firstName: string) => {
    const accounts = getAccounts();
    const key = email.toLowerCase();
    if (accounts[key]) throw new Error("An account with this email already exists.");
    if (password.length < 8) throw new Error("Password must be at least 8 characters.");
    const hash = await hashPassword(password);
    const id = crypto.randomUUID();
    accounts[key] = { hash, firstName: firstName.trim() || key.split("@")[0], id };
    localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(accounts));
    const user: AuthUser = { id, email: key, firstName: accounts[key].firstName };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(user));
    setState({ user, isLoaded: true });
  }, []);

  const signOut = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setState({ user: null, isLoaded: true });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
