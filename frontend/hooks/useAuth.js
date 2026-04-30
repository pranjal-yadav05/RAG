"use client";

import { useState, useCallback, useEffect } from "react";

const TOKEN_KEY = "lumina_access_token";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export function useAuth() {
  const [token, setToken] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [isHydrated, setIsHydrated] = useState(false);

  // Hydrate token from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) setToken(stored);
    setIsHydrated(true);
  }, []);

  const login = useCallback(async (email, password) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Invalid credentials");
      }
      const data = await res.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setToken(data.access_token);
      return true;
    } catch (e) {
      setAuthError(e.message);
      return false;
    } finally {
      setAuthLoading(false);
    }
  }, []);

  const signup = useCallback(async (email, password) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Signup failed");
      }
      const data = await res.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setToken(data.access_token);
      return true;
    } catch (e) {
      setAuthError(e.message);
      return false;
    } finally {
      setAuthLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("pdf_assistant_state");
    setToken(null);
  }, []);

  const clearAuthError = useCallback(() => setAuthError(null), []);

  return {
    token,
    isAuthenticated: !!token,
    isHydrated,
    authLoading,
    authError,
    login,
    signup,
    logout,
    clearAuthError,
  };
}