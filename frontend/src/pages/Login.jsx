import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { toast } from "sonner";

export default function Login() {
  const navigate = useNavigate();
  const { login, startGuest } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [magicLoading, setMagicLoading] = useState(false);
  const [magicSent, setMagicSent] = useState(false);

  const startDemo = async () => {
    setDemoLoading(true);
    try {
      await startGuest();
      toast.success("Welcome — you're in demo mode.");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not start demo mode.");
    } finally {
      setDemoLoading(false);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back.");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not sign in.");
    } finally {
      setLoading(false);
    }
  };

  const sendMagicLink = async () => {
    if (!email) {
      toast.error("Enter your email first.");
      return;
    }
    setMagicLoading(true);
    try {
      const r = await api.post("/auth/magic-link/request", { email });
      setMagicSent(true);
      if (r?.data?.mode === "signup") {
        toast.success("Check your inbox — we sent a link to set up your new account.");
      } else if (r?.data?.mode === "signin") {
        toast.success("Check your inbox — we sent a sign-in link.");
      } else {
        toast.success(r?.data?.message || "Check your inbox.");
      }
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 503) {
        toast.error(
          detail || "Email-based sign-in isn't available right now. Use your password instead."
        );
      } else if (status === 429) {
        toast.error(detail || "Too many requests. Please try again later.");
      } else {
        toast.error(detail || "Could not send a sign-in link right now.");
      }
    } finally {
      setMagicLoading(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-md fade-up">
        <Link to="/" className="block text-center mb-8" data-testid="brand-home-link">
          <svg width={68} height={68} viewBox="0 0 64 64" className="mx-auto mb-3" aria-hidden>
            <defs>
              <linearGradient id="loginBmGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#3D1A78" />
                <stop offset="55%" stopColor="#5E2DB5" />
                <stop offset="100%" stopColor="#2DB5B5" />
              </linearGradient>
            </defs>
            <path
              d="M32 56 C12 42, 4 30, 12 18 C18 9, 28 10, 32 18 C36 10, 46 9, 52 18 C60 30, 52 42, 32 56 Z"
              fill="url(#loginBmGrad)"
            />
            <circle cx="24" cy="26" r="4" fill="white" opacity="0.95" />
            <circle cx="40" cy="26" r="4" fill="white" opacity="0.95" />
            <path d="M22 36 Q32 44 42 36" stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.9" />
          </svg>
          <div className="font-sans font-extrabold text-3xl text-[#1A1330] tracking-tight">
            <span className="text-brand-gradient">SA</span> CoParents
          </div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[#857E9C] mt-1">
            Helping families communicate better
          </div>
        </Link>

        <div className="card-soft p-8 sm:p-10">
          <div className="eyebrow text-[#3D1A78] mb-3">Welcome back</div>
          <h1 className="font-sans font-extrabold text-4xl text-[#1A1330] mb-2 tracking-tight">Sign in</h1>
          <p className="text-[#4B4567] mb-6">
            Continue your preparation, exactly where you left it.
          </p>

          <button
            type="button"
            onClick={startDemo}
            disabled={demoLoading}
            className="btn-soft w-full flex items-center justify-center gap-3 mb-5 border-2 border-dashed border-[#3D1A78] text-[#3D1A78] font-semibold hover:bg-[#F1EBFA] disabled:opacity-60"
            data-testid="login-demo-mode-button"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M12 2l3 6 6 .9-4.5 4.3 1 6.3L12 16.9 6.5 19.5l1-6.3L3 8.9 9 8z" />
            </svg>
            {demoLoading ? "Starting demo…" : "Try the demo — no account needed"}
          </button>

          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 divider-line" />
            <span className="text-xs text-[#857E9C]">or sign in with email</span>
            <div className="flex-1 divider-line" />
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="eyebrow block mb-2">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-soft"
                placeholder="you@example.com"
                data-testid="login-email-input"
              />
              <button
                type="button"
                onClick={sendMagicLink}
                disabled={magicLoading || magicSent}
                className="mt-2 text-xs text-[#3D1A78] font-semibold hover:underline disabled:opacity-60"
                data-testid="login-magic-link-button"
              >
                {magicSent
                  ? "✓ Check your inbox"
                  : magicLoading
                  ? "Sending…"
                  : "Email me a link to sign in or set up an account"}
              </button>
            </div>
            <div>
              <label className="eyebrow block mb-2">Password</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-soft"
                placeholder="••••••••"
                data-testid="login-password-input"
              />
              <div className="mt-2 text-right">
                <Link
                  to="/forgot-password"
                  className="text-xs text-[#3D1A78] font-semibold hover:underline"
                  data-testid="login-forgot-password-link"
                >
                  Forgot password?
                </Link>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-gradient w-full"
              data-testid="login-submit-button"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 divider-line" />
            <span className="text-xs text-[#857E9C]">new here?</span>
            <div className="flex-1 divider-line" />
          </div>

          <Link
            to="/register"
            className="btn-soft w-full flex items-center justify-center gap-2 font-semibold"
            data-testid="login-create-account-button"
          >
            Create a new account
          </Link>

          <p className="text-xs text-[#857E9C] mt-4 text-center">
            Free to use. Takes about 30 seconds.
          </p>
        </div>
      </div>
    </div>
  );
}
