import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api, clearTokens, getAccessToken, getRefreshToken, setTokens } from "./api";
import type { TokenResponse, User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    state?: string;
    district?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function restore() {
      if (!getAccessToken() && !getRefreshToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.get<User>("/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        clearTokens();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.post<TokenResponse>("/auth/login", { email, password });
    setTokens(response.access_token, response.refresh_token);
    setUser(response.user);
  }, []);

  const register = useCallback(
    async (payload: {
      email: string;
      password: string;
      full_name: string;
      phone?: string;
      state?: string;
      district?: string;
    }) => {
      const response = await api.post<TokenResponse>("/auth/register", payload);
      setTokens(response.access_token, response.refresh_token);
      setUser(response.user);
    },
    [],
  );

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    try {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    } catch {
      // Local sign-out must still succeed if the network call fails.
    } finally {
      clearTokens();
      setUser(null);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await api.get<User>("/auth/me");
    setUser(me);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser, setUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
