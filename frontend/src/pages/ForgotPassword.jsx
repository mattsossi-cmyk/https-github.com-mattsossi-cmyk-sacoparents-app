import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, MailCheck } from "lucide-react";

import { api } from "../lib/api";
import { logError } from "../lib/logger";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      toast.error("Enter the email on your account.");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post("/auth/password-reset/request", {
        email: email.trim(),
      });
      setSent(true);
      toast.success(
        data?.message ||
          "If an account exists for that email, we sent a reset link."
      );
    } catch (err) {
      logError("password reset request failed", err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 503) {
        toast.error(
          detail || "Email isn't available right now. Please contact support."
        );
      } else if (status === 429) {
        toast.error(detail || "Too many requests. Please try again later.");
      } else {
        toast.error(detail || "Could not send a reset link right now.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-md fade-up">
        <Link
          to="/login"
          className="inline-flex items-center gap-1 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-4"
          data-testid="forgot-back-link"
        >
          <ArrowLeft size={12} /> Back to sign in
        </Link>

        <div className="card-soft p-8 sm:p-10" data-testid="forgot-password-page">
          {sent ? (
            <div className="text-center">
              <div className="w-12 h-12 mx-auto rounded-full bg-[#D5F2F2] grid place-items-center text-[#0E7A7A] mb-3">
                <MailCheck size={20} />
              </div>
              <h1 className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight">
                Check your inbox
              </h1>
              <p className="text-sm text-[#4B4567]">
                If an account exists for{" "}
                <span className="text-[#1A1330] font-medium">{email}</span>, we
                just sent a reset link. It expires in 15 minutes.
              </p>
              <p className="text-xs text-[#857E9C] mt-4">
                Didn't get it? Check spam, or wait a minute and try again.
              </p>
              <button
                onClick={() => {
                  setSent(false);
                  setEmail("");
                }}
                className="btn-soft w-full mt-6"
                data-testid="forgot-try-again-button"
              >
                Try a different email
              </button>
            </div>
          ) : (
            <>
              <div className="eyebrow text-[#3D1A78] mb-3">Forgot password</div>
              <h1 className="font-sans font-extrabold text-4xl text-[#1A1330] mb-2 tracking-tight">
                Reset your password
              </h1>
              <p className="text-[#4B4567] mb-6">
                Enter your email and we'll send you a link to choose a new
                password. It expires in 15 minutes.
              </p>

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
                    data-testid="forgot-email-input"
                    autoFocus
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-gradient w-full"
                  data-testid="forgot-submit-button"
                >
                  {loading ? "Sending…" : "Send reset link"}
                </button>
              </form>

              <p className="text-xs text-[#857E9C] mt-6 text-center">
                Remembered your password?{" "}
                <Link
                  to="/login"
                  className="text-[#3D1A78] font-semibold hover:underline"
                >
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
