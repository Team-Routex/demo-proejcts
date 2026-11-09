"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, UserStats } from "@/types";
import { api, getToken, setToken } from "./api";

interface AuthContextType {
  user: User | null;
  stats: UserStats | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (data: { identifier?: string; email?: string; username?: string; password: string }) => Promise<void>;
  register: (data: { username: string; email: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setStats(null);
      setIsLoading(false);
      return;
    }
    try {
      const res: any = await api.auth.me();
      const currentUser = res?.user || res;
      const currentStats = res?.stats || currentUser?.stats || null;
      if (currentUser && currentUser.id) {
        setUser(currentUser);
        setStats(currentStats);
      } else {
        setToken(null);
        setUser(null);
        setStats(null);
      }
    } catch {
      setToken(null);
      setUser(null);
      setStats(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (data: { identifier?: string; email?: string; username?: string; password: string }) => {
    const res = await api.auth.login(data);
    if (res && res.token) {
      setToken(res.token);
      setUser(res.user);
      if ((res.user as any)?.stats) {
        setStats((res.user as any).stats);
      }
      try {
        await refreshUser();
      } catch {
        // preserve existing user from login response
      }
    }
  };

  const register = async (data: { username: string; email: string; password: string; full_name?: string }) => {
    const res = await api.auth.register(data);
    if (res && res.token) {
      setToken(res.token);
      setUser(res.user);
      if ((res.user as any)?.stats) {
        setStats((res.user as any).stats);
      }
      try {
        await refreshUser();
      } catch {
        // preserve existing user from register response
      }
    }
  };

  const logout = async () => {
    await api.auth.logout();
    setUser(null);
    setStats(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        stats,
        isLoading,
        isAuthenticated: !!user,
        isAdmin: user?.role === "admin",
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

