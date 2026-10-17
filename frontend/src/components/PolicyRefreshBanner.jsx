/**
 * PolicyRefreshBanner — one-time in-app announcement of the 2026-02-21
 * privacy-policy rewrite (the "Private by Default. Shared by Choice."
 * 32-section canonical policy).
 *
 * Visible only for RETURNING parents (account created before the
 * policy effective date) who haven't dismissed this specific version
 * yet. Version-keyed so any future policy revision reappears the
 * banner without wiping older dismissals.
 *
 * Deliberately NOT rendered:
 *   - When the user is unauthenticated (nothing to announce yet).
 *   - When the user is a fresh signup after the effective date (they
 *     already agreed at registration).
 *   - When the user is in a guest sandbox (guest UI is intentionally
 *     minimal; policy prompts happen at claim time instead).
 *   - When the user is already on /privacy (redundant).
 *
 * Persistence uses localStorage — this is a UX preference, not
 * sensitive personal data, and matches the pattern used by
 * IntroTourModal / VerificationBanner elsewhere in the codebase.
 */
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { X, ShieldCheck, ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

// Bump the version suffix any time the canonical Privacy Policy at
// /privacy is materially revised. The dismissal key is scoped to that
// version so returning users see a fresh banner on the next refresh.
const POLICY_VERSION = "2026-02-21";
const DISMISS_KEY = `sa_policy_refresh_v_${POLICY_VERSION}`;
const EFFECTIVE_DATE_ISO = "2026-02-21T00:00:00Z";

export default function PolicyRefreshBanner() {
  const { user } = useAuth();
  const location = useLocation();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    try {
      if (window.localStorage.getItem(DISMISS_KEY) === "true") {
        setDismissed(true);
      }
    } catch {
      // Private-mode / storage-denied — treat as not dismissed. Worst
      // case, the parent sees the banner every session; the link is
      // still helpful and dismissing is one click.
    }
  }, []);

  const dismiss = () => {
    setDismissed(true);
    try { window.localStorage.setItem(DISMISS_KEY, "true"); } catch { /* ignore */ }
  };

  // Gate conditions — evaluated after hooks so the hook order is stable.
  if (dismissed) return null;
  if (!user) return null;                                    // not logged in
  if (user.is_guest) return null;                            // guest sandbox
  if (location.pathname.startsWith("/privacy")) return null; // redundant on the policy page
  if (location.pathname.startsWith("/legal/")) return null;  // redundant on any legal page

  // Only show for RETURNING parents — accounts created BEFORE the
  // policy effective date. Fresh signups agreed to the new text at
  // registration; showing them a "refresh" banner would be confusing.
  const createdAt = user.created_at ? Date.parse(user.created_at) : NaN;
  const effectiveAt = Date.parse(EFFECTIVE_DATE_ISO);
  if (!Number.isFinite(createdAt) || createdAt >= effectiveAt) return null;

  return (
    <div
      className="w-full bg-gradient-to-r from-[#F1EAFF] via-[#F8F7FC] to-[#E8F6F5] border-b border-[#E5E0EE]"
      role="status"
      aria-live="polite"
      data-testid="policy-refresh-banner"
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-start sm:items-center gap-3">
        <div className="hidden sm:grid place-items-center w-9 h-9 shrink-0 rounded-full bg-white border border-[#E5E0EE] text-[#3D1A78]">
          <ShieldCheck size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Privacy policy refreshed
          </div>
          <div className="text-sm text-[#1A1330] font-semibold leading-snug">
            Private by Default. Shared by Choice.
          </div>
          <div className="text-[0.75rem] text-[#4B4567] leading-snug mt-0.5">
            We rewrote the policy in plain English before you next share
            a report — take a minute to skim what&apos;s protected, what
            isn&apos;t, and how sharing actually works.
          </div>
        </div>
        <Link
          to="/privacy"
          onClick={dismiss}
          data-testid="policy-refresh-read-link"
          className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-xs font-semibold hover:bg-[#2A0F5F] transition shrink-0"
        >
          Read the policy <ArrowRight size={12} />
        </Link>
        <Link
          to="/privacy"
          onClick={dismiss}
          aria-label="Read the refreshed privacy policy"
          data-testid="policy-refresh-read-link-mobile"
          className="sm:hidden text-xs font-semibold text-[#3D1A78] underline shrink-0"
        >
          Read
        </Link>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss privacy policy refresh banner"
          data-testid="policy-refresh-dismiss"
          className="w-8 h-8 grid place-items-center rounded-full text-[#4B4567] hover:bg-white/60 shrink-0"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
