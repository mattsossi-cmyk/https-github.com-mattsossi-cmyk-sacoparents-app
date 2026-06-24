import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";

/**
 * Protected route — but never asks the user to "sign in".
 *
 * If there is no active session, we silently start a guest (demo) session so
 * the visitor lands directly inside the app and can save their work. This is
 * the SACOParents product promise: every page is reachable in demo mode,
 * nobody is forced to create an account just to try the prep wizard.
 *
 * The guest session is created via POST /api/auth/guest which sets an
 * httpOnly cookie and returns the user — `startGuest` updates the auth
 * context so the protected children render on the next pass.
 */
export default function ProtectedRoute({ children }) {
  const { user, loading, startGuest } = useAuth();
  const [bootstrapping, setBootstrapping] = useState(false);
  const [bootstrapError, setBootstrapError] = useState(null);
  const attemptedRef = useRef(false);

  useEffect(() => {
    if (loading) return;
    if (user) return;
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
  }, [user, loading, startGuest]);

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
