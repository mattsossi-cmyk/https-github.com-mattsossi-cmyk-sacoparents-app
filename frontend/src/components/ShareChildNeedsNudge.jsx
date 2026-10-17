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
 *
 * Retry cadence (iter189):
 *   Each case tile carries a per-user ✕ dismiss. A dismissed tile
 *   hides for exactly 7 days, then reappears ONCE. If the parent
 *   dismisses it again, we honour that and hide it permanently.
 *   State lives in localStorage under `snc2.childNeedsShareNudge.dismissed`
 *   as `{ [caseId]: { dismissedAt: ISO, retried: boolean } }`.
 *   Granting consent (checking the box) clears the dismissal entirely
 *   — the parent has engaged, no more nudging needed.
 *   If a case's consent is REVOKED (my_consent_at becomes null on
 *   the server), the dismiss state is NOT auto-restored — the tile
 *   simply comes back in the nudge; the parent can re-dismiss it
 *   and the 7-day cycle starts fresh.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Users, Check, Loader2, X } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";


const DISMISS_STORAGE_KEY = "snc2.childNeedsShareNudge.dismissed";
const DISMISS_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function readDismissState() {
  try {
    const raw = localStorage.getItem(DISMISS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (err) {
    // localStorage disabled / private mode / parse error — treat as
    // "nothing dismissed yet" so the nudge still surfaces.
    logError("ShareChildNeedsNudge: could not read dismiss state", err);
    return {};
  }
}

function writeDismissState(next) {
  try {
    localStorage.setItem(DISMISS_STORAGE_KEY, JSON.stringify(next));
  } catch (err) {
    // Storage full or private mode — the dismiss just won't survive
    // reload. Non-fatal.
    logError("ShareChildNeedsNudge: could not persist dismiss state", err);
  }
}

/**
 * Returns true iff a case tile should be HIDDEN right now given its
 * dismiss record. Semantics:
 *   - no record       → show
 *   - first dismiss + within 7 days → HIDE
 *   - first dismiss + > 7 days      → SHOW (retry)
 *   - second dismiss  → HIDE permanently (retried=true)
 */
function isDismissed(record, nowMs) {
  if (!record || !record.dismissedAt) return false;
  const dismissedMs = Date.parse(record.dismissedAt);
  if (Number.isNaN(dismissedMs)) return false;
  if (record.retried) return true;
  return nowMs - dismissedMs < DISMISS_TTL_MS;
}


export default function ShareChildNeedsNudge() {
  const [cases, setCases] = useState(null); // null = loading, [] = none, [...] = list
  const [pendingCaseId, setPendingCaseId] = useState(null);
  const [error, setError] = useState(null);
  // Editable microcopy — fetched from `/public/nudge-copy/child-needs-share`.
  // Falls back to the hardcoded defaults on any error so a backend
  // hiccup can never blank out the nudge card.
  const [copy, setCopy] = useState({
    headline: "Share these highlights with your co-parent's joint report?",
    subhead:
      "By default your Child Needs highlights stay private. If you toggle this on for a case, section 5 of the joint Complete Alignment Report only surfaces your highlights *after* your co-parent also toggles it on. You can revoke anytime.",
  });
  // Local mirror of localStorage so setState re-renders the list. We
  // hydrate once on mount — the SNCv2 report page isn't visited
  // simultaneously in two tabs, so cross-tab sync isn't worth the
  // storage-event plumbing.
  const [dismissMap, setDismissMap] = useState(() => readDismissState());

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
    // Fetch admin-editable copy — non-blocking, silent fallback.
    api
      .get("/public/nudge-copy/child-needs-share")
      .then((r) => {
        if (cancelled) return;
        const h = r.data?.headline;
        const s = r.data?.subhead;
        if (h && s) setCopy({ headline: h, subhead: s });
      })
      .catch((err) => {
        // Non-fatal — we already have the defaults in state.
        logError("share-child-needs nudge: fetch copy failed", err);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const nowMs = Date.now();

  // Filter cases through the dismiss map — but track whether each
  // hidden tile is on its "retry" cool-down (so the parent's Q1
  // grant-clears semantic still applies if they later re-toggle).
  // `nowMs` is deliberately excluded from deps: it changes every
  // render (defeating memoization) and only matters for a 7-day TTL
  // check that a stale value can't meaningfully affect within a
  // single React reconciliation.
  const visibleCases = useMemo(() => {
    if (!cases) return null;
    return cases.filter((c) => !isDismissed(dismissMap[c.case_id], nowMs));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cases, dismissMap]);

  const dismissCase = (caseId) => {
    const prev = dismissMap[caseId];
    // Second dismiss (retry window already elapsed → tile came back
    // → parent dismissed AGAIN) → mark retried=true so it stays
    // hidden forever. First dismiss records the timestamp only.
    const isRetryDismissal = !!(prev && prev.dismissedAt);
    const next = {
      ...dismissMap,
      [caseId]: isRetryDismissal
        ? { dismissedAt: new Date().toISOString(), retried: true }
        : { dismissedAt: new Date().toISOString(), retried: false },
    };
    setDismissMap(next);
    writeDismissState(next);
    // Fire-and-forget analytics event so admins can see whether the
    // retry cadence is converting hesitant parents (first_total vs
    // permanent_total on /api/analytics/admin/overview).
    api
      .post(
        `/complete-report/joint/${caseId}/nudge-dismiss`,
        null,
        { params: { is_retry_dismissal: isRetryDismissal } },
      )
      .catch((err) => {
        // Non-fatal — the UI dismiss must still succeed even if the
        // event write fails.
        logError("share-child-needs nudge: dismiss event failed", err);
      });
  };

  const clearDismiss = (caseId) => {
    if (!dismissMap[caseId]) return;
    const next = { ...dismissMap };
    delete next[caseId];
    setDismissMap(next);
    writeDismissState(next);
  };

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
      // Q1: granting consent clears any prior dismissal for this
      // case, so the retry cycle resets cleanly.
      if (newConsentAt) clearDismiss(caseId);
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
  // Every visible case has been dismissed (either mid-cool-down or
  // permanently). Whole component hides.
  if (visibleCases && visibleCases.length === 0) return null;

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
            {copy.headline}
          </h3>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            {copy.subhead}
          </p>
        </div>
      </div>

      <ul
        className="mt-4 space-y-2"
        data-testid="child-needs-share-nudge-cases"
      >
        {(visibleCases || []).map((c) => {
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
              className="relative rounded-2xl border border-[#EEE8F7] bg-white p-3 sm:p-4 flex items-start gap-3"
              data-testid={`child-needs-share-nudge-case-${c.case_id}`}
            >
              <label className="flex items-start gap-3 cursor-pointer flex-1 pr-6">
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
                      <span className="text-[#8A5500]">{status}</span>
                    ) : (
                      <span className="text-[#6E6787]">{status}</span>
                    )}
                  </div>
                </div>
              </label>
              {isPending && (
                <Loader2 size={14} className="animate-spin text-[#3D1A78] mt-1.5" />
              )}
              <button
                type="button"
                onClick={() => dismissCase(c.case_id)}
                aria-label={`Hide this share prompt for ${c.case_id}`}
                data-testid={`child-needs-share-nudge-dismiss-${c.case_id}`}
                className="absolute top-2 right-2 inline-flex items-center justify-center w-6 h-6 rounded-full text-[#6E6787] hover:bg-[#F1EBFA] hover:text-[#3D1A78] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              >
                <X size={12} />
              </button>
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

      <p className="mt-3 text-[11px] text-[#6E6787] italic leading-relaxed">
        Educational and organizational — not a diagnosis, not a court
        submission. You can change this any time from the joint report
        page.
      </p>
    </section>
  );
}
