"use client";

// Client-side auth: the JWT lives in localStorage and is attached manually
// to each API call. This is the simplest thing that works for an MVP
// scaffold, but it's NOT the most secure long-term choice -- an httpOnly
// cookie set by the backend (with the backend also handling CSRF
// protection) would prevent the token from ever being readable by
// injected JS. Swapping this out is a backend + frontend co-change, noted
// in README.md's "Next steps".

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ApiError, getCurrentUser } from "./api";
import type { User } from "./types";

const TOKEN_STORAGE_KEY = "taxengine_token";

interface AuthContextValue {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadUser(activeToken: string) {
    try {
      const currentUser = await getCurrentUser(activeToken);
      setUser(currentUser);
    } catch (err) {
      // Only a confirmed 401 means the token itself is invalid/expired --
      // drop it rather than leaving the app in a half-authenticated state.
      // Anything else (network error, backend temporarily unreachable,
      // ...) is NOT proof the session is dead, so the token stays in
      // localStorage and a later retry (refreshUser, a page reload) can
      // recover it instead of forcing a needless re-login.
      if (err instanceof ApiError && err.status === 401) {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
      }
      setUser(null);
    }
  }

  useEffect(() => {
    // Reading localStorage (a client-only synchronous store) and seeding
    // React state from it MUST happen in an effect, not during render --
    // `window` doesn't exist during Next.js's server-rendered first pass,
    // so there is no earlier point this can happen without breaking SSR.
    const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (stored) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setToken(stored);
      loadUser(stored).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  async function login(newToken: string) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
    await loadUser(newToken);
  }

  function logout() {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }

  async function refreshUser() {
    if (token) await loadUser(token);
  }

  return (
    <AuthContext.Provider value={{ token, user, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
