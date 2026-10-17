import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, MailCheck, KeyRound } from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import CodeInput from "../components/CodeInput";
import PasswordStrengthMeter, {
  scorePassword,
} from "../components/PasswordStrengthMeter";

/**
 * ForgotPassword — 6-digit in-app code flow.
 *
 * Step 1 (email): user submits their email; backend mints and emails a
 *   6-digit code, then always returns 200 to preserve account privacy.
 * Step 2 (code + new password): user enters the 6 digits + a new
 *   password. Server verifies via bcrypt, rotates the password, marks
 *   email_verified, invalidates all outstanding auth tokens for the user,
 *   and signs the user in with a fresh JWT.
 */
export default function ForgotPassword() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [confirming, setConfirming] = useState(false);

  // One-click deep-link from the reset email: /forgot-password?email=X&code=Y
  // Pre-fills both fields and jumps straight to the "set new password"
  // step so the parent doesn't have to re-type the code.
  useEffect(() => {
    const emailFromUrl = (searchParams.get("email") || "").trim();
    const codeFromUrl = (searchParams.get("code") || "").replace(/\D/g, "").slice(0, 6);
    if (emailFromUrl && codeFromUrl.length === 6) {
      setEmail(emailFromUrl);
      setCode(codeFromUrl);
      setStep("code");
    }
  // Intentionally run once at mount — subsequent state changes shouldn't
  // reset the flow if the parent has already moved past step 1.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const requestCode = async (e) => {
    e?.preventDefault?.();
    if (!email.trim()) {
      toast.error("Enter the email on your account.");
      return;
    }
    setRequesting(true);
    try {
      const { data } = await api.post("/auth/password-reset/request-code", {
        email: email.trim(),
      });
      toast.success(
        data?.message ||
          "If an account exists for that email, we sent a 6-digit code.",
      );
      setStep("code");
    } catch (err) {
      logError("password reset code request failed", err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 429) {
        toast.error(detail || "Too many reset requests. Try again later.");
      } else {
        toast.error(detail || "Could not send a reset code right now.");
      }
    } finally {
      setRequesting(false);
    }
  };

  const confirmCode = async (e) => {
    e?.preventDefault?.();
    if (code.length !== 6) {
      toast.error("Enter the full 6-digit code.");
      return;
    }
    if (scorePassword(password).score < 2) {
      toast.error("Please choose a stronger password.");
      return;
    }
    setConfirming(true);
    try {
      await api.post("/auth/password-reset/confirm-code", {
        email: email.trim(),
        code,
        password,
      });
      toast.success("Password updated — you're signed in.");
      // Refresh the auth context so the app knows we're logged in.
      try {
        await checkAuth();
      } catch (e) {
        logError("checkAuth after reset failed", e);
      }
      navigate("/dashboard", { replace: true });
    } catch (err) {
      logError("password reset code confirm failed", err);
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Invalid or expired code.");
    } finally {
      setConfirming(false);
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
          {step === "email" ? (
            <>
              <div className="eyebrow text-[#3D1A78] mb-3">Forgot password</div>
              <h1 className="font-sans font-extrabold text-4xl text-[#1A1330] mb-2 tracking-tight">
                Reset your password
              </h1>
              <p className="text-[#4B4567] mb-6">
                Enter your email and we'll send you a 6-digit code to type
                right here. It expires in 15 minutes.
              </p>

              <form onSubmit={requestCode} className="space-y-4">
                <div>
                  <label className="eyebrow block mb-2">Email</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(ev) => setEmail(ev.target.value)}
                    className="input-soft"
                    placeholder="you@example.com"
                    data-testid="forgot-email-input"
                    autoFocus
                  />
                </div>
                <button
                  type="submit"
                  disabled={requesting}
                  className="btn-gradient w-full"
                  data-testid="forgot-submit-button"
                >
                  {requesting ? "Sending…" : "Send 6-digit code"}
                </button>
              </form>

              <p className="text-xs text-[#6E6787] mt-6 text-center">
                Remembered your password?{" "}
                <Link
                  to="/login"
                  className="text-[#3D1A78] font-semibold hover:underline"
                >
                  Sign in
                </Link>
              </p>
            </>
          ) : (
            <>
              <div className="w-12 h-12 mx-auto rounded-full bg-[#F1EEF7] grid place-items-center text-[#3D1A78] mb-3">
                <KeyRound size={20} />
              </div>
              <div className="eyebrow text-[#3D1A78] mb-3 text-center">
                Step 2 of 2
              </div>
              <h1 className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight text-center">
                Enter your code
              </h1>
              <p className="text-sm text-[#4B4567] text-center mb-6">
                We sent 6 digits to{" "}
                <span className="text-[#1A1330] font-medium">{email}</span>.
                Type them below to set a new password.
              </p>

              <form onSubmit={confirmCode} className="space-y-5">
                <div>
                  <label className="eyebrow block mb-3 text-center">
                    Verification code
                  </label>
                  <CodeInput
                    value={code}
                    onChange={setCode}
                    onComplete={() => {
                      // Auto-focus the password field once the code is
                      // filled — feels snappier than making the user tab.
                      const pw = document.querySelector(
                        '[data-testid="forgot-new-password-input"]',
                      );
                      pw?.focus();
                    }}
                    testidPrefix="forgot-code"
                    disabled={confirming}
                  />
                </div>

                <div>
                  <label className="eyebrow block mb-2">New password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(ev) => setPassword(ev.target.value)}
                    className="input-soft"
                    placeholder="At least 8 characters"
                    data-testid="forgot-new-password-input"
                  />
                  <PasswordStrengthMeter
                    password={password}
                    testid="forgot-password-strength"
                  />
                </div>

                <button
                  type="submit"
                  disabled={confirming || code.length !== 6}
                  className="btn-gradient w-full"
                  data-testid="forgot-confirm-button"
                >
                  {confirming ? "Saving…" : "Save new password & sign in"}
                </button>
              </form>

              <div className="mt-6 flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setCode("");
                    setPassword("");
                    setStep("email");
                  }}
                  className="text-[#6E6787] hover:text-[#3D1A78]"
                  data-testid="forgot-change-email-button"
                >
                  Use a different email
                </button>
                <button
                  type="button"
                  onClick={requestCode}
                  disabled={requesting}
                  className="text-[#3D1A78] font-semibold hover:underline disabled:opacity-60"
                  data-testid="forgot-resend-code-button"
                >
                  {requesting ? "Resending…" : "Resend code"}
                </button>
              </div>

              <div className="mt-4 pt-4 border-t border-[#EFECF6] text-center">
                <MailCheck size={12} className="inline text-[#0E7A7A] mr-1" />
                <span className="text-[0.6875rem] text-[#6E6787]">
                  Didn't get the email? Check spam, then resend.
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
