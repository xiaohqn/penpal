import { createContext, ReactNode, useContext, useMemo, useState } from "react";

import { buildApiUrl } from "../lib/api-base";

export type UserRole = "counselor" | "visitor";

export type AuthUser = {
  id: number;
  username: string;
  role: UserRole;
  counselorId: string;
  displayName: string;
};

type StoredAuth = {
  token: string;
  user: AuthUser;
};

type AuthContextValue = {
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  register: (payload: { username: string; password: string; displayName: string; role: UserRole; inviteCode: string }) => Promise<void>;
  logout: () => void;
};

const STORAGE_KEY = "mindful-copilot-auth";
const AuthContext = createContext<AuthContextValue | null>(null);

function formatAuthError(detail: unknown) {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") {
          return String(item);
        }
        const error = item as { loc?: unknown[]; msg?: string };
        const field = error.loc?.at(-1);
        return `${field ? `${String(field)}：` : ""}${error.msg ?? "输入内容有误"}`;
      })
      .join("；");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return "认证失败";
}

function readStoredAuth(): StoredAuth | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredAuth) : null;
  } catch {
    return null;
  }
}

async function authRequest(path: string, body: unknown) {
  const response = await fetch(buildApiUrl(`/api/v1/auth/${path}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(formatAuthError(data?.detail));
  }
  const data = (await response.json()) as {
    token: string;
    user: { id: number; username: string; display_name: string; role: UserRole };
  };
  const stored: StoredAuth = {
    token: data.token,
    user: {
      id: data.user.id,
      username: data.user.username,
      counselorId: data.user.username,
      displayName: data.user.display_name,
      role: data.user.role,
    },
  };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  return stored;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredAuth()?.user ?? null);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      async login(username, password) {
        const stored = await authRequest("login", { username, password });
        setUser(stored.user);
      },
      async register(payload) {
        const stored = await authRequest("register", {
          username: payload.username,
          password: payload.password,
          display_name: payload.displayName,
          role: payload.role,
          invite_code: payload.inviteCode,
        });
        setUser(stored.user);
      },
      logout() {
        window.localStorage.removeItem(STORAGE_KEY);
        setUser(null);
      },
    }),
    [user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

export function getStoredAuthToken() {
  return readStoredAuth()?.token ?? "";
}

export function getStoredCounselorId() {
  return readStoredAuth()?.user.username ?? "default";
}

export function getStoredUserId() {
  return readStoredAuth()?.user.username ?? "visitor";
}

export function getAuthHeaders(): Record<string, string> {
  const token = getStoredAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
