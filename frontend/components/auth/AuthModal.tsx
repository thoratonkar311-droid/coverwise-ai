"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { ShieldCheck, X, Mail, Lock, User as UserIcon, AlertCircle, Loader2 } from "lucide-react";

export function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, authModalTab, login, register } = useAuth();
  const [localTab, setLocalTab] = useState<"login" | "register" | null>(null);
  const tab = localTab ?? authModalTab;
  const setTab = (t: "login" | "register") => setLocalTab(t);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isAuthModalOpen) {
        setLocalTab(null);
        setError(null);
        closeAuthModal();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isAuthModalOpen, closeAuthModal]);

  if (!isAuthModalOpen) return null;

  const handleClose = () => {
    setLocalTab(null);
    setError(null);
    closeAuthModal();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client validation
    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    if (!password || password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setLoading(true);
    try {
      if (tab === "login") {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), password, fullName.trim() || undefined);
      }
      // Reset fields
      setEmail("");
      setPassword("");
      setFullName("");
      setError(null);
      setLocalTab(null);
    } catch (err: unknown) {
      const errObj = err as { message?: string; detail?: string } | undefined;
      const msg =
        errObj?.message ||
        errObj?.detail ||
        (tab === "login"
          ? "Invalid email or password. Please verify your credentials."
          : "Could not create account. Email may already be registered.");
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200/80 overflow-hidden transform transition-all animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-gradient-to-b from-[#EEF4FF] to-white px-6 pt-6 pb-4 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0052D1] to-[#1769FF] flex items-center justify-center text-white shadow-xs">
                <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
              </div>
              <div>
                <span className="text-base font-bold tracking-tight text-[#0A1D2E]">
                  CoverWise<span className="text-[#1769FF]">.ai</span>
                </span>
                <span className="block text-[11px] text-slate-500 font-medium">
                  Policy Intelligence
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={handleClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              aria-label="Close dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-4">
            <h2 id="auth-modal-title" className="text-xl font-bold text-[#0A1D2E]">
              {tab === "login" ? "Welcome back" : "Create an account"}
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              {tab === "login"
                ? "Sign in to access your saved policies, coverage analyses, and dashboard."
                : "Register to securely persist and analyze your insurance policies."}
            </p>
          </div>

          {/* Tab Selector */}
          <div className="flex items-center p-1 mt-4 rounded-xl bg-slate-100/90 border border-slate-200/60">
            <button
              type="button"
              onClick={() => {
                setTab("login");
                setError(null);
              }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                tab === "login"
                  ? "bg-white text-[#0052D1] shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setTab("register");
                setError(null);
              }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                tab === "register"
                  ? "bg-white text-[#0052D1] shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Create Account
            </button>
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs animate-in fade-in duration-100">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {tab === "register" && (
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-700" htmlFor="auth-fullname">
                Full Name <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  id="auth-fullname"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jane Doe"
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 bg-white placeholder-slate-400 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1769FF] focus:border-transparent transition-all"
                  disabled={loading}
                />
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700" htmlFor="auth-email">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
              <input
                id="auth-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 bg-white placeholder-slate-400 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1769FF] focus:border-transparent transition-all"
                disabled={loading}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold text-slate-700" htmlFor="auth-password">
                Password
              </label>
              {tab === "register" && (
                <span className="text-[11px] text-slate-400">Min. 6 characters</span>
              )}
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
              <input
                id="auth-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 bg-white placeholder-slate-400 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1769FF] focus:border-transparent transition-all"
                disabled={loading}
              />
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="md"
            className="w-full justify-center font-semibold mt-2"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                {tab === "login" ? "Signing in..." : "Creating account..."}
              </span>
            ) : tab === "login" ? (
              "Sign In"
            ) : (
              "Create Account"
            )}
          </Button>

          <div className="text-center pt-2">
            {tab === "login" ? (
              <p className="text-xs text-slate-600">
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setTab("register");
                    setError(null);
                  }}
                  className="font-semibold text-[#0052D1] hover:underline cursor-pointer"
                >
                  Create an account
                </button>
              </p>
            ) : (
              <p className="text-xs text-slate-600">
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setTab("login");
                    setError(null);
                  }}
                  className="font-semibold text-[#0052D1] hover:underline cursor-pointer"
                >
                  Sign in
                </button>
              </p>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
