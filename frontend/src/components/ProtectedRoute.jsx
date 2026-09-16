import React, { useEffect, useRef, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

/**
 * Protected route — usually silent guest-bootstrap.
 *
 * Default behavior: if there is no active session, silently start a
 * guest (demo) session so the visitor lands directly inside the app
 * and can save their work. This is the SACOParents product promise.
 *
 * Iter197 · Court-ordered case deep-link recovery.
 * Pass `requireRealUser` on routes that MUST be the parent's real
 * account (e.g. `/case/:caseId` — a guest identity would 403 on the
 * case lookup anyway). For those, redirect to
 * `/login?redirect=<current-path>` so an expired-cookie parent
 * signing back in lands right back on the page they came for.
 */
export default function ProtectedRoute({ children, requireRealUser = false }) {
  const { user, loading, startGuest } = useAuth();
  const location = useLocation();
  const [bootstrapping, setBootstrapping] = useState(false);
  const [bootstrapError, setBootstrapError] = useState(null);
  const attemptedRef = useRef(false);

  const shouldGuestBootstrap = !requireRealUser;

  useEffect(() => {
    if (loading) return;
    if (user) return;
    if (!shouldGuestBootstrap) return;
    if (attemptedRef.current) return;
    attemptedRef.current = true;
    setBootstrapping(true);
    startGuest()
      .catch((err) => {
        logError("Auto guest bootstrap failed:", err);
        setBootstrapError(
          err?.response?.data?.detail ||
            "Couldn't open the demo right now. Please refresh the page."
        );
      })
      .finally(() => setBootstrapping(false));
  }, [user, loading, startGuest, shouldGuestBootstrap]);

  // Deep-link recovery: signed-out visitor on a real-user route →
  // bounce to /login carrying the target path so the post-login
  // navigate lands them right back here. `location.pathname` +
  // `search` preserves any query params the invite link carried.
  if (!loading && !user && !shouldGuestBootstrap) {
    const target = `${location.pathname}${location.search || ""}`;
    return <Navigate to={`/login?redirect=${encodeURIComponent(target)}`} replace />;
  }

  if (loading || bootstrapping || (!user && !bootstrapError)) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[#4B4567]">
        <div className="animate-pulse text-sm tracking-[0.2em] uppercase">
          Loading
        </div>
      </div>
    );
  }

  if (!user && bootstrapError) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div
          className="max-w-md w-full bg-white rounded-2xl shadow-md border border-[#E5E0EE] p-8 text-center"
          data-testid="guest-bootstrap-error"
        >
          <h1 className="font-sans font-bold text-2xl text-[#1A1330] mb-2">
            We couldn&apos;t open your demo
          </h1>
          <p className="text-sm text-[#4B4567] mb-5">{bootstrapError}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center justify-center px-5 py-2.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm"
            data-testid="guest-bootstrap-retry-button"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return children;
}
