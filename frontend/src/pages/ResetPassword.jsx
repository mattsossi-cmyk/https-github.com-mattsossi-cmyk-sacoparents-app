import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import PasswordStrengthMeter, { scorePassword } from "../components/PasswordStrengthMeter";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const token = params.get("token") || "";

  const [validating, setValidating] = useState(true);
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [password, setPassword] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setError("Missing reset token. Please request a new reset link.");
      setValidating(false);
      return;
    }
    api
      .get("/auth/password-reset/preview", { params: { token } })
      .then(({ data }) => {
        if (cancelled) return;
        setEmail(data.email || "");
      })
      .catch((err) => {
        if (cancelled) return;
        logError("reset preview failed", err);
        setError(
          err?.response?.data?.detail ||
            "This reset link is invalid or has expired."
        );
      })
      .finally(() => {
        if (!cancelled) setValidating(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    if (scorePassword(password).score < 2) {
      toast.error("Please choose a stronger password.");
      return;
    }
    if (password !== confirmPwd) {
      toast.error("Passwords don't match.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/auth/password-reset/confirm", { token, password });
      // Cookie is set by the backend; refresh AuthContext.
      try {
        await checkAuth?.();
      } catch (e) {
        logError("auth refresh after reset failed", e);
      }
      toast.success("Password updated. You're signed in.");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      logError("password reset confirm failed", err);
      toast.error(
        err?.response?.data?.detail || "Could not reset password. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-md fade-up">
        <div className="card-soft p-8 sm:p-10" data-testid="reset-password-page">
          {validating ? (
            <div className="text-center py-10 text-sm tracking-[0.2em] uppercase text-[#6E6787]">
              <Loader2 size={16} className="inline animate-spin mr-2" /> Verifying link…
            </div>
          ) : error ? (
            <div className="text-center">
              <div className="w-12 h-12 mx-auto rounded-full bg-[#FCE3DC] grid place-items-center text-[#9A3A23] mb-3">
                <AlertCircle size={20} />
              </div>
              <h1 className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight">
                Link not valid
              </h1>
              <p className="text-sm text-[#4B4567]" data-testid="reset-error-message">
                {error}
              </p>
              <Link
                to="/forgot-password"
                className="btn-gradient w-full inline-flex items-center justify-center mt-6"
                data-testid="reset-request-new-button"
              >
                Request a new reset link
              </Link>
            </div>
          ) : (
            <>
              <div className="eyebrow text-[#3D1A78] mb-3 flex items-center gap-1.5">
                <CheckCircle2 size={12} /> Link verified
              </div>
              <h1 className="font-sans font-extrabold text-4xl text-[#1A1330] mb-2 tracking-tight">
                Choose a new password
              </h1>
              <p className="text-[#4B4567] mb-6">
                Setting a new password for{" "}
                <span className="text-[#1A1330] font-medium">{email}</span>.
              </p>

              <form onSubmit={onSubmit} className="space-y-4">
                <div>
                  <label className="eyebrow block mb-2">New password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-soft"
                    placeholder="At least 8 characters"
                    autoFocus
                    data-testid="reset-password-input"
                  />
                  <PasswordStrengthMeter
                    password={password}
                    testid="reset-password-strength"
                  />
                </div>
                <div>
                  <label className="eyebrow block mb-2">Confirm new password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={confirmPwd}
                    onChange={(e) => setConfirmPwd(e.target.value)}
                    className="input-soft"
                    placeholder="Re-enter password"
                    data-testid="reset-password-confirm-input"
                  />
                </div>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-gradient w-full"
                  data-testid="reset-submit-button"
                >
                  {submitting ? "Saving…" : "Update password & sign in"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
