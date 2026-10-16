import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { ConsentFields, consentReady, emptyConsent } from "./ConsentFields";

// Public and recipient-facing pages that never need the consent screen.
const OPEN_PATHS = new Set([
  "/privacy-notice", "/privacy", "/privacy-policy", "/confidentiality", "/terms", "/accessibility", "/methodology",
  "/data-retention", "/safety", "/what-professionals-see", "/watch", "/legacy", "/for-portal-engineers", "/for-professionals",
  "/login", "/register", "/signup", "/claim", "/forgot-password", "/reset-password", "/verify-email",
]);
const OPEN_PREFIXES = ["/auth/", "/invite/", "/verify/", "/doc/", "/shared/", "/joint-agreement/shared/", "/joint-report/shared/", "/foundation/shared/", "/survey/", "/legal/", "/samples", "/join/sample-preview"];

export const consentScreenApplies = (user, pathname) =>
  !!user && !user.consent_current && !OPEN_PATHS.has(pathname) && !OPEN_PREFIXES.some((p) => pathname.startsWith(p));

const quickExit = () => {
  try {
    window.location.replace("https://www.weather.com/");
  } catch {
    /* best-effort */
  }
};

function ConsentScreen() {
  const { checkAuth, logout } = useAuth();
  const [value, setValue] = useState(emptyConsent);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const headingRef = useRef(null);
  useEffect(() => headingRef.current?.focus(), []);
  const submit = async (e) => {
    e.preventDefault();
    if (!consentReady(value)) return;
    setBusy(true);
    setError("");
    try {
      await api.post("/privacy-consent", value);
      await checkAuth();
    } catch (err) {
      setError(typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Couldn't save that. Please try again.");
      setBusy(false);
    }
  };
  return (
    <main data-testid="consent-screen" className="min-h-screen gentle-bg grid place-items-center p-4 sm:p-6">
      <div className="w-full max-w-lg card-soft p-6 sm:p-8 fade-up">
        <div className="flex justify-end mb-2">
          <button type="button" onClick={quickExit} data-testid="consent-quick-exit" className="text-xs font-bold px-3 py-1.5 rounded-full bg-[#B71F70] text-white hover:bg-[#9a1a5e]">
            Quick Exit
          </button>
        </div>
        <h1 ref={headingRef} tabIndex={-1} className="font-sans font-extrabold text-2xl sm:text-3xl text-[#1A1330] tracking-tight mb-2 outline-none">
          Before you continue
        </h1>
        <p className="text-[#4B4567] text-sm mb-5">Please read the Privacy Notice and tick both boxes to continue.</p>
        <form onSubmit={submit} className="space-y-4">
          <ConsentFields tp="consent-screen" value={value} onChange={setValue} />
          {error && <p data-testid="consent-screen-error" role="alert" className="text-sm text-[#B71F70]">{error}</p>}
          <button type="submit" disabled={!consentReady(value) || busy} data-testid="consent-screen-continue" className="btn-gradient w-full disabled:opacity-50 disabled:cursor-not-allowed">
            {busy ? "Saving…" : "Continue"}
          </button>
        </form>
        <button type="button" onClick={logout} data-testid="consent-screen-sign-out" className="mt-4 w-full text-center text-xs text-[#4B4567] underline">
          Sign out
        </button>
      </div>
    </main>
  );
}

// Keeps signed-in users (including demo sessions and Google sign-ins) out of the app until both boxes are ticked.
export function ConsentGate({ children }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  return consentScreenApplies(user, pathname) ? <ConsentScreen /> : children;
}
