import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

export default function Login() {
  const navigate = useNavigate();
  const { login, loginWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

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
            <span className="text-brand-gradient">SACO</span>Parents
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
            onClick={loginWithGoogle}
            className="btn-soft w-full flex items-center justify-center gap-3 mb-5"
            data-testid="google-login-button"
          >
            <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
              <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 35 24 35c-6.1 0-11-4.9-11-11s4.9-11 11-11c2.8 0 5.4 1.1 7.3 2.8l5.7-5.7C33.6 6.7 29 5 24 5 13.5 5 5 13.5 5 24s8.5 19 19 19 19-8.5 19-19c0-1.2-.1-2.3-.4-3.5z" />
              <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 13 24 13c2.8 0 5.4 1.1 7.3 2.8l5.7-5.7C33.6 6.7 29 5 24 5 16.3 5 9.8 9.1 6.3 14.7z" />
              <path fill="#4CAF50" d="M24 43c5 0 9.5-1.6 13-4.3l-6-5.1c-1.9 1.4-4.4 2.4-7 2.4-5.2 0-9.7-3.5-11.3-8.3l-6.5 5C9.8 38.9 16.3 43 24 43z" />
              <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.3 5.6l6 5.1C40.9 35 44 30 44 24c0-1.2-.1-2.3-.4-3.5z" />
            </svg>
            Continue with Google
          </button>

          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 divider-line" />
            <span className="text-xs text-[#857E9C]">or with email</span>
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

          <p className="text-sm text-[#4B4567] mt-6 text-center">
            New here?{" "}
            <Link to="/register" className="text-[#3D1A78] font-semibold hover:underline" data-testid="login-to-register-link">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
