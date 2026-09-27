"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as authApi from "@/lib/api/auth";
import {
  clearTokens,
  getCachedUser,
  getRefreshToken,
  hasSession,
  setCachedUser,
  setTokens,
} from "@/lib/auth/token-storage";
import type { LoginPayload, RegisterPayload, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Optimistically show a cached user (if any) for instant frame-0
  // rendering, but isLoading stays true until refreshUser has actually
  // confirmed that session against the backend -- ProtectedRoute waits
  // for that before deciding whether to redirect, so a stale/expired
  // cached user never gets treated as "logged in" by anything that
  // matters.
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = useCallback(async () => {
    if (!hasSession()) {
      setUser(null);
      clearTokens();
      setIsLoading(false);
      return;
    }
    try {
      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
      setCachedUser(currentUser);
    } catch {
      // The access token is missing, expired, or otherwise invalid.
      // This must NOT keep showing a cached/fake user as if the session
      // were fine -- that's exactly what silently broke route protection
      // before: isAuthenticated was hardcoded true regardless of whether
      // this check ever actually succeeded.
      setUser(null);
      clearTokens();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (payload: LoginPayload) => {
    setIsLoading(true);
    try {
      const tokens = await authApi.login(payload);
      setTokens(tokens);
      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
      setCachedUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    setIsLoading(true);
    try {
      await authApi.register(payload);
      await login({ email: payload.email, password: payload.password });
    } finally {
      setIsLoading(false);
    }
  }, [login]);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {}
    }
    clearTokens();
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
