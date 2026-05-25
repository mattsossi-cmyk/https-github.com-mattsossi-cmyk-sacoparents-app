import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const processed = useRef(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || "";
    const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
    const sessionId = params.get("session_id");

    if (!sessionId) {
      setError({
        title: "Sign-in didn't complete",
        message:
          "We didn't receive a session from Google. This usually means the browser blocked the redirect, or you closed the Google window before finishing.",
        code: "missing_session_id",
      });
      return;
    }

    (async () => {
      try {
        await api.post(
          "/auth/google/session",
          {},
          { headers: { "X-Session-ID": sessionId } }
        );
        await checkAuth();
        navigate("/dashboard", { replace: true });
      } catch (err) {
        logError("Google session exchange failed:", err);
        const status = err?.response?.status;
        const detail = err?.response?.data?.detail;
        setError({
          title: "We couldn't finish signing you in",
          message:
            status === 401
              ? "Google verified you, but our server couldn't validate the session. This often happens when a sign-in link is reused or expires after a few seconds."
              : detail ||
                "Something went wrong while securing your session. Please try again.",
          code: status ? `http_${status}` : "exchange_failed",
        });
      }
    })();
  }, [navigate, checkAuth]);

  if (error) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center p-6">
        <div
          className="w-full max-w-md card-soft p-8 text-center fade-up"
          data-testid="auth-callback-error"
        >
          <div className="text-xs uppercase tracking-[0.25em] text-[#B07A6A] mb-3">
            Sign-in interrupted
          </div>
          <h1 className="font-serif text-2xl text-[#1A1330] mb-3">
            {error.title}
          </h1>
          <p className="text-[#4B4567] mb-6">{error.message}</p>
          <div className="flex flex-col gap-3">
            <Link
              to="/login"
              replace
              className="btn-sage w-full"
              data-testid="auth-callback-back-to-login"
            >
              Back to sign in
            </Link>
            <Link
              to="/"
              replace
              className="text-sm text-[#3D1A78] hover:underline"
            >
              Return home
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
      <div className="text-center" data-testid="auth-callback-loading">
        <div className="text-xs uppercase tracking-[0.25em] text-[#857E9C] mb-3">
          Securing your session
        </div>
        <div className="font-serif text-2xl text-[#1A1330]">One moment…</div>
      </div>
    </div>
  );
}
