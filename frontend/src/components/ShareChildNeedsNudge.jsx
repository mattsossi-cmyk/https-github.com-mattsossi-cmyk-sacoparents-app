/**
 * ShareChildNeedsNudge — post-completion nudge on the Child Needs
 * Statement (SNC v2) report page.
 *
 * Product intent: When a parent finishes their Child Needs
 * Statement AND they're currently on one or more active joint
 * cases, we prompt them right there — "Want to share these
 * highlights with your co-parent's joint report?" — with a per-case
 * toggle so they can grant consent while the context is freshest.
 *
 * Privacy: The nudge writes to the SAME
 * `child_needs_share_consent_at` field the joint viewer's checkbox
 * uses, via the SAME `POST /api/complete-report/joint/{case_id}/consent/child-needs`
 * endpoint — so this component is just a friendlier entry point,
 * not a second consent surface. Everything the aggregator scrub +
 * dual-consent gate does still applies.
 *
 * If the parent is on ZERO active joint cases, the whole component
 * returns null so the report page doesn't sprout an empty prompt.
 */
import React, { useEffect, useState } from "react";
import { Users, Check, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";


export default function ShareChildNeedsNudge() {
  const [cases, setCases] = useState(null); // null = loading, [] = none, [...] = list
  const [pendingCaseId, setPendingCaseId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/complete-report/my-active-cases")
      .then((r) => {
        if (!cancelled) setCases(r.data?.cases || []);
      })
      .catch((err) => {
        if (cancelled) return;
        logError("share-child-needs nudge: fetch cases failed", err);
        // Silent fail — the nudge is optional; don't block the page.
        setCases([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleCase = async (caseId) => {
    setPendingCaseId(caseId);
    setError(null);
    try {
      const r = await api.post(`/complete-report/joint/${caseId}/consent/child-needs`);
      const newConsentAt = r.data?.my_consent_at || null;
      // Update local list — the endpoint already returned my new state.
      setCases((prev) =>
        (prev || []).map((c) =>
          c.case_id === caseId ? { ...c, my_consent_at: newConsentAt } : c
        )
      );
    } catch (err) {
      logError("share-child-needs nudge: toggle failed", err);
      setError("We couldn't save your preference. Please try again in a moment.");
    } finally {
      setPendingCaseId(null);
    }
  };

  // Loading — don't show a spinner (feels heavier than the nudge itself).
  if (cases === null) return null;
  // Zero active joint cases → hide the whole component. The parent
  // will see the same toggle inside the joint viewer if they're
  // added to a case later.
  if (cases.length === 0) return null;

  return (
    <section
      className="mt-8 rounded-3xl border-2 border-[#D6CFE8] bg-gradient-to-br from-[#FAF6FF] to-[#F1E7FA] p-5 sm:p-6"
      data-testid="child-needs-share-nudge"
      aria-labelledby="child-needs-share-nudge-heading"
    >
      <div className="flex items-start gap-3">
        <div className="rounded-full bg-white/70 p-2 mt-0.5 shrink-0">
          <Users size={16} className="text-[#3D1A78]" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Optional · you're in control
          </div>
          <h3
            id="child-needs-share-nudge-heading"
            className="font-serif text-lg sm:text-xl text-[#1A1330] mt-1 leading-snug"
          >
            Share these highlights with your co-parent's joint report?
          </h3>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            By default your Child Needs highlights stay private. If you
            toggle this on for a case, section 5 of the joint Complete
            Alignment Report only surfaces your highlights <em>after</em>{" "}
            your co-parent also toggles it on. You can revoke anytime.
          </p>
        </div>
      </div>

      <ul
        className="mt-4 space-y-2"
        data-testid="child-needs-share-nudge-cases"
      >
        {cases.map((c) => {
          const isOn = !!c.my_consent_at;
          const isPending = pendingCaseId === c.case_id;
          const status = isOn
            ? c.coparent_has_consented
              ? "Both consented · unlocked"
              : "Waiting on your co-parent"
            : c.coparent_has_consented
            ? "Your co-parent has consented · your turn"
            : "Neither has consented yet";
          return (
            <li
              key={c.case_id}
              className="rounded-2xl border border-[#EEE8F7] bg-white p-3 sm:p-4 flex items-start gap-3"
              data-testid={`child-needs-share-nudge-case-${c.case_id}`}
            >
              <label className="flex items-start gap-3 cursor-pointer flex-1">
                <input
                  type="checkbox"
                  checked={isOn}
                  disabled={isPending}
                  onChange={() => toggleCase(c.case_id)}
                  className="mt-1 h-4 w-4 rounded border-[#3D1A78] text-[#3D1A78] focus:ring-[#3D1A78]"
                  data-testid={`child-needs-share-nudge-toggle-${c.case_id}`}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-semibold text-[#1A1330]">
                    {c.case_id}
                    <span className="text-[#4B4567] font-normal">
                      {" "}
                      · with {c.coparent_name}
                    </span>
                  </div>
                  <div
                    className="text-[11px] uppercase tracking-[0.14em] font-bold mt-1"
                    data-testid={`child-needs-share-nudge-status-${c.case_id}`}
                  >
                    {isOn && c.coparent_has_consented ? (
                      <span className="text-[#1E6A42] inline-flex items-center gap-1">
                        <Check size={11} /> {status}
                      </span>
                    ) : isOn || c.coparent_has_consented ? (
                      <span className="text-[#AA6A00]">{status}</span>
                    ) : (
                      <span className="text-[#857E9C]">{status}</span>
                    )}
                  </div>
                </div>
              </label>
              {isPending && (
                <Loader2 size={14} className="animate-spin text-[#3D1A78] mt-1.5" />
              )}
            </li>
          );
        })}
      </ul>

      {error && (
        <div
          className="mt-3 text-[12px] text-[#AA0033]"
          data-testid="child-needs-share-nudge-error"
        >
          {error}
        </div>
      )}

      <p className="mt-3 text-[11px] text-[#857E9C] italic leading-relaxed">
        Educational and organizational — not a diagnosis, not a court
        submission. You can change this any time from the joint report
        page.
      </p>
    </section>
  );
}
