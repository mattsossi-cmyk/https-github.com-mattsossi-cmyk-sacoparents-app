import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Mail, Check, ArrowLeft, Send } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

/**
 * Passwordless email-based signup. The parent enters their email,
 * receives a one-time setup link, and clicks it to finish creating
 * their account on /auth/setup.
 */
export default function SignUp() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [errMsg, setErrMsg] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return;
    const trimmed = email.trim().toLowerCase();
    if (!trimmed) {
      setErrMsg("Please enter your email address.");
      return;
    }
    setLoading(true);
    setErrMsg(null);
    try {
      const r = await api.post("/auth/magic-link/request", { email: trimmed });
      setSent(true);
      // Show different copy depending on whether we actually mailed signup vs signin
      if (r?.data?.mode === "signin") {
        // server tells us this email already has an account — magic link is signin
        setErrMsg(null);
      }
    } catch (err) {
      logError("magic link request failed:", err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 503) {
        // SMTP not configured — give a clear signup-context message instead
        // of the backend's "Email sign-in isn't available" wording.
        setErrMsg(
          "Email setup links aren't available on this deployment yet. " +
          "We're working on it. In the meantime, tap " +
          '"Enter the App without an account" below to start using SA CoParents right away.'
        );
      } else if (status === 429) {
        setErrMsg(detail || "Too many requests. Please wait a few minutes and try again.");
      } else {
        setErrMsg(detail || "Couldn't send the setup link right now. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-md fade-up">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-[#4B4567] hover:text-[#1A1330] mb-6"
          data-testid="signup-back-link"
        >
          <ArrowLeft size={14} /> Back
        </Link>

        <div className="card-soft p-8 sm:p-10">
          {!sent ? (
            <>
              <div className="w-12 h-12 rounded-full bg-[#EFE9F9] grid place-items-center text-[#3D1A78] mb-4">
                <Mail size={20} />
              </div>
              <div className="eyebrow text-[#3D1A78] mb-2">Create your account</div>
              <h1
                className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight"
                data-testid="signup-heading"
              >
                We'll email you a setup link.
              </h1>
              <p className="text-[#4B4567] mt-3 leading-relaxed">
                Enter your email. We'll send you a one-time link to finish setting up your account — no passwords to remember up front.
              </p>

              <form onSubmit={submit} className="mt-7 space-y-4">
                <div>
                  <label className="eyebrow block mb-2" htmlFor="signup-email">
                    Email
                  </label>
                  <input
                    id="signup-email"
                    type="email"
                    required
                    autoFocus
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input-soft"
                    placeholder="you@example.com"
                    data-testid="signup-email-input"
                  />
                </div>

                {errMsg && (
                  <div
                    className="text-sm text-[#9B3B3B] bg-[#FBECEC] border border-[#F1C7C7] rounded-xl px-3 py-2"
                    data-testid="signup-error"
                  >
                    {errMsg}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-gradient w-full inline-flex items-center justify-center gap-2 disabled:opacity-60"
                  data-testid="signup-submit-button"
                >
                  {loading ? "Sending…" : (
                    <>
                      Email me a setup link <Send size={14} />
                    </>
                  )}
                </button>
              </form>

              <div className="flex items-center gap-3 my-6">
                <div className="flex-1 divider-line" />
                <span className="text-xs text-[#857E9C]">or</span>
                <div className="flex-1 divider-line" />
              </div>

              <Link
                to="/"
                className="btn-soft w-full inline-flex items-center justify-center gap-2 font-semibold"
                data-testid="signup-enter-instead-link"
              >
                Enter the App without an account
              </Link>
              <p className="text-xs text-[#857E9C] mt-3 text-center">
                You can always upgrade to a saved account later.
              </p>
            </>
          ) : (
            <>
              <div className="w-12 h-12 rounded-full bg-[#D5F2F2] grid place-items-center text-[#0E7A7A] mb-4">
                <Check size={22} />
              </div>
              <div className="eyebrow text-[#0E7A7A] mb-2">Check your inbox</div>
              <h1
                className="font-sans font-extrabold text-3xl sm:text-4xl text-[#1A1330] tracking-tight"
                data-testid="signup-sent-heading"
              >
                We just sent you a link.
              </h1>
              <p className="text-[#4B4567] mt-3 leading-relaxed">
                We sent a setup link to <strong>{email}</strong>. It will expire in 15 minutes. Open the email on this device and tap the link to finish creating your account.
              </p>
              <p className="text-sm text-[#857E9C] mt-4">
                Don't see it? Check your spam folder. You can also{" "}
                <button
                  type="button"
                  onClick={() => {
                    setSent(false);
                    setErrMsg(null);
                  }}
                  className="text-[#3D1A78] font-semibold hover:underline"
                  data-testid="signup-try-different-email-button"
                >
                  use a different email
                </button>
                .
              </p>

              <Link
                to="/"
                className="btn-soft w-full inline-flex items-center justify-center gap-2 font-semibold mt-8"
                data-testid="signup-sent-back-link"
              >
                Back to home
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
