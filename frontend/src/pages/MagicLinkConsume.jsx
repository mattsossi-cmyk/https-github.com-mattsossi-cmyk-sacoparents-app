import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

export default function MagicLinkConsume() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const processed = useRef(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const token = params.get("token");
    if (!token) {
      setError({
        title: "Missing sign-in token",
        message: "The link you opened doesn't contain a valid token. Try requesting a new one from the login page.",
        code: "missing_token",
      });
      return;
    }
    (async () => {
      try {
        await api.post("/auth/magic-link/consume", { token });
        await checkAuth();
        navigate("/dashboard", { replace: true });
      } catch (err) {
        logError("Magic-link consume failed:", err);
        const status = err?.response?.status;
        const detail = err?.response?.data?.detail;
        setError({
          title: "We couldn't sign you in with this link",
          message:
            detail ||
            (status === 400
              ? "Your sign-in link is invalid, expired, or already used."
              : "Something went wrong. Please request a new sign-in link."),
          code: status ? `http_${status}` : "consume_failed",
        });
      }
    })();
  }, [params, navigate, checkAuth]);

  if (error) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center p-6">
        <div className="w-full max-w-md card-soft p-8 text-center fade-up" data-testid="magic-error">
          <div className="text-xs uppercase tracking-[0.25em] text-[#B07A6A] mb-3">
            Sign-in interrupted
          </div>
          <h1 className="font-serif text-2xl text-[#1A1330] mb-3">{error.title}</h1>
          <p className="text-[#4B4567] mb-6">{error.message}</p>
          <div className="flex flex-col gap-3">
            <Link to="/login" replace className="btn-sage w-full" data-testid="magic-back-to-login">
              Back to sign in
            </Link>
          </div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#A7B3AD] mt-6">
            Code: {error.code}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gentle-bg grid place-items-center">
      <div className="text-center" data-testid="magic-loading">
        <div className="text-xs uppercase tracking-[0.25em] text-[#857E9C] mb-3">
          Signing you in
        </div>
        <div className="font-serif text-2xl text-[#1A1330]">One moment…</div>
      </div>
    </div>
  );
}
