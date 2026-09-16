import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { toast } from "sonner";

/**
 * Login — Demo-first entry point.
 *
 * The primary action is "Enter demo mode" so any visitor can try the app
 * with no account. A collapsed section still exposes email + password
 * sign-in (used by the admin account and returning users who prefer it),
 * but it's intentionally out of the way.
 *
 * Iter197 · honours a `?redirect=<path>` query param so deep-link
 * recovery (e.g. an expired-cookie parent tapping their `/case/:caseId`
 * email link) lands them back on the page they were headed to instead
 * of the generic `/dashboard`. Only same-origin relative paths are
 * followed — never redirect to an off-site URL.
 */
function _safeRedirect(target) {
  if (!target) return null;
  const t = String(target).trim();
  // Same-origin relative paths only. Reject empty, protocol-relative,
  // and absolute URLs so a phishing crafted `?redirect=//evil.com/…`
  // never bounces the parent off the app.
  if (!t.startsWith("/") || t.startsWith("//")) return null;
  return t;
}

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTo = _safeRedirect(searchParams.get("redirect")) || "/dashboard";
  const { login, startGuest } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [magicLoading, setMagicLoading] = useState(false);
  const [magicSent, setMagicSent] = useState(false);
  const [showEmail, setShowEmail] = useState(false);

  const startDemo = async () => {
    setDemoLoading(true);
    try {
      await startGuest();
      toast.success("Welcome — you're in demo mode.");
      navigate(redirectTo);
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
      navigate(redirectTo);
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
          detail || "Email-based sign-in isn't available right now."
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
          <div className="eyebrow text-[#3D1A78] mb-3">Welcome</div>
          <h1 className="font-sans font-extrabold text-4xl text-[#1A1330] mb-2 tracking-tight">
            Enter demo mode
          </h1>
          <p className="text-[#4B4567] mb-6">
            Try the full app instantly — no account, no email, no password.
            Your work stays in this browser session so you can explore freely.
          </p>

          <button
            type="button"
            onClick={startDemo}
            disabled={demoLoading}
            className="btn-gradient w-full flex items-center justify-center gap-3 disabled:opacity-60"
            data-testid="login-demo-mode-button"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M12 2l3 6 6 .9-4.5 4.3 1 6.3L12 16.9 6.5 19.5l1-6.3L3 8.9 9 8z" />
            </svg>
            {demoLoading ? "Starting demo…" : "Enter demo mode"}
          </button>

          <p className="text-[11px] text-[#857E9C] mt-3 text-center">
            No account needed · Free to use · Takes 2 seconds
          </p>

          {/* Advanced: email + password sign-in (collapsed). Kept for the
              admin account and returning users with saved credentials. */}
          <div className="mt-8 pt-6 border-t border-[#EFECF6]">
            {!showEmail ? (
              <button
                type="button"
                onClick={() => setShowEmail(true)}
                className="w-full text-xs text-[#857E9C] hover:text-[#3D1A78]"
                data-testid="login-show-email-toggle"
              >
                Have an existing account? <span className="font-semibold underline">Sign in with email</span>
              </button>
            ) : (
              <div>
                <div className="text-xs text-[#857E9C] mb-4">
                  Existing account sign-in
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
                        : "Email me a sign-in link instead"}
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
                    className="btn-soft w-full font-semibold"
                    data-testid="login-submit-button"
                  >
                    {loading ? "Signing in…" : "Sign in"}
                  </button>
                </form>
                <button
                  type="button"
                  onClick={() => setShowEmail(false)}
                  className="mt-4 w-full text-[11px] text-[#857E9C] hover:text-[#3D1A78]"
                  data-testid="login-hide-email-toggle"
                >
                  ← Back to demo mode
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
