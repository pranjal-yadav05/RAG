"use client";

import { useState, useEffect, useRef } from "react";
import { Loader2, Eye, EyeOff, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AuthModal({ onLogin, onSignup, authLoading, authError, onClearError }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState(null);
  const emailRef = useRef(null);

  useEffect(() => {
    emailRef.current?.focus();
  }, [mode]);

  useEffect(() => {
    if (authError) setLocalError(authError);
  }, [authError]);

  const clearErrors = () => {
    setLocalError(null);
    onClearError?.();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearErrors();

    if (!email.trim()) return setLocalError("Email is required");
    if (!password) return setLocalError("Password is required");
    if (mode === "signup" && password.length < 3)
      return setLocalError("Password must be at least 3 characters");

    if (mode === "login") {
      await onLogin(email.trim(), password);
    } else {
      await onSignup(email.trim(), password);
    }
  };

  const switchMode = () => {
    clearErrors();
    setEmail("");
    setPassword("");
    setMode((m) => (m === "login" ? "signup" : "login"));
  };

  return (
    /* Backdrop */
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      {/* Modal card */}
      <div className="relative w-full max-w-sm mx-4 bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 fade-in duration-200">

        {/* Decorative top bar */}
        <div className="h-0.5 w-full bg-gradient-to-r from-transparent via-primary/60 to-transparent" />

        {/* Header */}
        <div className="px-8 pt-8 pb-6 text-center">
          <div className="flex items-baseline justify-center gap-1.5 mb-1">
            <span className="text-2xl font-semibold tracking-tight [font-family:var(--font-playfair)]">
              Lumina
            </span>
            <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
              RAG
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {mode === "login"
              ? "Sign in to continue"
              : "Create your account"}
          </p>
        </div>

        {/* Tab switcher */}
        <div className="mx-8 mb-6 flex rounded-lg bg-muted/40 border border-border/50 p-1">
          {["login", "signup"].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { clearErrors(); setMode(m); setEmail(""); setPassword(""); }}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                mode === m
                  ? "bg-background shadow-sm text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}>
              {m === "login" ? "Sign In" : "Sign Up"}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-8 pb-8 space-y-4">
          {/* Email */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Email
            </label>
            <input
              ref={emailRef}
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); clearErrors(); }}
              placeholder="you@example.com"
              autoComplete="email"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all"
            />
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => { setPassword(e.target.value); clearErrors(); }}
                placeholder="••••••••"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className="w-full px-3 py-2 pr-10 rounded-lg border border-input bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Error */}
          {localError && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 animate-in fade-in slide-in-from-top-1 duration-200">
              <span className="text-xs text-destructive leading-relaxed">{localError}</span>
            </div>
          )}

          {/* Submit */}
          <Button
            type="submit"
            disabled={authLoading}
            className="w-full mt-2">
            {authLoading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : null}
            {authLoading
              ? "Please wait..."
              : mode === "login"
              ? "Sign In"
              : "Create Account"}
          </Button>

          {/* Switch mode */}
          <p className="text-center text-xs text-muted-foreground pt-1">
            {mode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={switchMode}
              className="text-primary hover:underline font-medium transition-colors">
              {mode === "login" ? "Sign Up" : "Sign In"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}