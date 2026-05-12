import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const res = await api.get("/auth/me");
      setUser(res.data);
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Critical: if returning from Emergent OAuth, AuthCallback will exchange the
    // session_id and establish the session. Skip /me check to avoid a race.
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    localStorage.setItem("sa_access_token", res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (payload) => {
    const res = await api.post("/auth/register", payload);
    localStorage.setItem("sa_access_token", res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const loginWithGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/auth/callback";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch (e) { /* ignore */ }
    localStorage.removeItem("sa_access_token");
    setUser(null);
  };

  const updateProfile = async (payload) => {
    const res = await api.patch("/auth/profile", payload);
    setUser(res.data);
    return res.data;
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, loginWithGoogle, logout, updateProfile, checkAuth }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
