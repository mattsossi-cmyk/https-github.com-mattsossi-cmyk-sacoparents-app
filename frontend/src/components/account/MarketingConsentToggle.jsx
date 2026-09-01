/**
 * MarketingConsentToggle — HB 300 §181.152 marketing opt-in switch.
 *
 * Under HB 300, marketing communications that use PHI require
 * affirmative opt-in. Default is OFF; this toggle is the ONLY way
 * a parent can flip the flag on. Every change is written to the
 * PHI access log server-side so an auditor can reconstruct the
 * exact moment of opt-in/opt-out.
 *
 * Data flow:
 *   GET  /api/me/hb300/status         → current opt-in state
 *   POST /api/me/hb300/marketing      → { opt_in: bool }
 *
 * Optimistic UI (flip immediately, revert on failure) so the
 * toggle feels responsive. Toast confirms both success and revert.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Loader2, Megaphone } from "lucide-react";
import { api } from "../../lib/api";
import { toast } from "sonner";


export default function MarketingConsentToggle() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [optIn, setOptIn] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/me/hb300/status");
      setOptIn(!!data?.marketing_opt_in);
    } catch {
      // Silently degrade — the toggle just stays at its default (off)
      // rather than blocking the whole page over a status ping.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const toggle = async () => {
    if (saving) return;
    const next = !optIn;
    setSaving(true);
    setOptIn(next);  // optimistic
    try {
      const { data } = await api.post("/me/hb300/marketing", { opt_in: next });
      setOptIn(!!data?.opt_in);
      setUpdatedAt(data?.updated_at || null);
      toast.success(
        next
          ? "You'll now receive occasional SA CoParents updates."
          : "You've opted out of marketing emails. You'll still get transactional messages (share links, receipts, etc.)."
      );
    } catch (err) {
      // Roll back the optimistic flip and surface the reason.
      setOptIn(!next);
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Couldn't update your preference right now.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5"
      data-testid="marketing-consent-panel"
    >
      <div className="flex items-start gap-3">
        <div
          className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]"
          aria-hidden
        >
          <Megaphone size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
            Communication preferences
          </div>
          <div className="text-sm font-semibold text-[#1A1330] mt-0.5 leading-tight">
            Occasional SA CoParents updates
          </div>
          <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">
            New features, policy changes, and tips written for co-parents.
            <br className="hidden sm:block" />
            {" "}Transactional emails (share links, receipts, HB&nbsp;300 notices)
            will keep coming regardless.
          </p>
        </div>
        <button
          type="button"
          onClick={toggle}
          disabled={loading || saving}
          role="switch"
          aria-checked={optIn}
          aria-label="Toggle marketing email opt-in"
          data-testid="marketing-consent-toggle"
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2 disabled:opacity-60 ${optIn ? "bg-[#3D1A78]" : "bg-[#D6CFE8]"}`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${optIn ? "translate-x-[22px]" : "translate-x-[2px]"}`}
            aria-hidden
          />
          {(loading || saving) && (
            <Loader2
              size={10}
              className="animate-spin absolute left-1/2 -translate-x-1/2 text-white"
              aria-hidden
            />
          )}
        </button>
      </div>
      <div className="mt-3 pl-12 flex items-center gap-2 text-[10px] text-[#857E9C]">
        <span
          className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 border border-[#E5E0EE] bg-[#FCFBFE]"
          data-testid="marketing-consent-state"
        >
          {loading ? "Checking..." : optIn ? "Currently opted IN" : "Currently opted OUT"}
        </span>
        <span className="italic">
          HB&nbsp;300 §181.152 — every change is timestamped in your PHI access log.
        </span>
      </div>
    </div>
  );
}
