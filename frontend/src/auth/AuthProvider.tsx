import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useI18n } from "../i18n/I18nProvider";
import { api, getToken, setToken } from "../lib/api";
import type { Language, Role, User } from "../lib/types";

interface RegisterInput {
  name: string;
  email: string;
  password: string;
  role: Extract<Role, "customer" | "seller">;
}

interface AuthValue {
  user: User | null;
  isLoading: boolean;
  isCustomer: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (input: RegisterInput) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { lang, setLang } = useI18n();
  const [token, setTokenState] = useState<string | null>(getToken);

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: () => api<User>("/auth/me"),
    enabled: Boolean(token),
    staleTime: 5 * 60_000,
  });

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
    queryClient.removeQueries();
  }, [queryClient]);

  // The API client fires this when the server rejects an expired token.
  useEffect(() => {
    const onExpired = () => logout();
    window.addEventListener("shopsense:logout", onExpired);
    return () => window.removeEventListener("shopsense:logout", onExpired);
  }, [logout]);

  const startSession = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        form: { username: email, password },
      });
      setToken(access_token);
      setTokenState(access_token);
      const user = await queryClient.fetchQuery({ queryKey: ["me", access_token], queryFn: () => api<User>("/auth/me") });
      // Adopt the account's saved language if it's one the UI supports.
      if (["en", "hi", "mr"].includes(user.preferred_language)) setLang(user.preferred_language as Language);
      return user;
    },
    [queryClient, setLang],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      await api<User>("/auth/register", { method: "POST", json: { ...input, preferred_language: lang } });
      return startSession(input.email, input.password);
    },
    [lang, startSession],
  );

  const value = useMemo<AuthValue>(() => {
    const user = token ? (me.data ?? null) : null;
    return {
      user,
      isLoading: Boolean(token) && me.isLoading,
      isCustomer: user?.role === "customer",
      login: startSession,
      register,
      logout,
    };
  }, [token, me.data, me.isLoading, startSession, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
