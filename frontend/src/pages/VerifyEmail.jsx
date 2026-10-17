import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { user, checkAuth } = useAuth();
  const ran = useRef(false);
  const [stage, setStage] = useState("loading"); // loading | success | error
  const [error, setError] = useState(null);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const token = params.get("token");
    if (!token) {
      setError("Missing verification token. Please use the link from your email.");
      setStage("error");
      return;
    }
    api
      .post("/auth/verify-email/confirm", { token })
      .then(async () => {
        // Refresh auth context so the verified flag flips immediately.
        try {
          await checkAuth?.();
        } catch (e) {
          logError("verify checkAuth failed", e);
        }
        setStage("success");
      })
      .catch((err) => {
        logError("verify confirm failed", err);
        setError(
          err?.response?.data?.detail ||
            "This verification link is invalid or has expired."
        );
        setStage("error");
      });
    // Intentional: this effect must run exactly once on mount to consume
    // the token. `api`, setters, and logError are stable; adding them would
    // either no-op or risk double-consuming the token.
  }, [params, checkAuth]);

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-md fade-up">
        <div className="card-soft p-8 sm:p-10 text-center" data-testid="verify-email-page">
          {stage === "loading" && (
            <>
              <div className="w-12 h-12 mx-auto rounded-full bg-[#EFE9F9] grid place-items-center text-[#3D1A78] mb-3">
                <Loader2 size={20} className="animate-spin" />
              </div>
              <h1 className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight">
                Confirming your email…
              </h1>
              <p className="text-sm text-[#4B4567]">One moment.</p>
            </>
          )}
          {stage === "success" && (
            <>
              <div className="w-12 h-12 mx-auto rounded-full bg-[#D5F2F2] grid place-items-center text-[#0E7A7A] mb-3">
                <CheckCircle2 size={20} />
              </div>
              <h1
                className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight"
                data-testid="verify-success-title"
              >
                Email confirmed
              </h1>
              <p className="text-sm text-[#4B4567]">
                Thanks for confirming. Your account is now fully verified.
              </p>
              <button
                onClick={() => navigate(user ? "/dashboard" : "/login", { replace: true })}
                className="btn-gradient w-full mt-6"
                data-testid="verify-success-continue-button"
              >
                {user ? "Go to dashboard" : "Sign in"}
              </button>
            </>
          )}
          {stage === "error" && (
            <>
              <div className="w-12 h-12 mx-auto rounded-full bg-[#FCE3DC] grid place-items-center text-[#9A3A23] mb-3">
                <AlertCircle size={20} />
              </div>
              <h1 className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight">
                Link not valid
              </h1>
              <p className="text-sm text-[#4B4567]" data-testid="verify-error-message">
                {error}
              </p>
              <Link
                to={user ? "/dashboard" : "/login"}
                className="btn-gradient w-full inline-flex items-center justify-center mt-6"
                data-testid="verify-error-back-button"
              >
                {user ? "Go to dashboard" : "Back to sign in"}
              </Link>
              {user && !user.email_verified && (
                <p className="text-xs text-[#6E6787] mt-3">
                  You can request a new verification email from the banner on your
                  dashboard.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
