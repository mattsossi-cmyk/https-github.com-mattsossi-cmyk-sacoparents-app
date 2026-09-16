/**
 * CourtOrderedCaseBadge — iter196.
 *
 * When a parent has previously linked a court-ordered case via
 * `/join`, we stash the `case_id` in localStorage so this badge can
 * offer a persistent one-tap jump back into the scoped `/case/:caseId`
 * view from anywhere on the dashboard.
 *
 * Silently renders nothing when:
 *   - no case_id is in localStorage
 *   - localStorage is unavailable (private browsing)
 *   - a subsequent dashboard visit clears the flag
 *
 * The parent can dismiss the badge — that clears the stored case_id
 * so it doesn't come back on the next visit. They can always re-enter
 * their code at `/join` to bring the badge back.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Scale, X } from "lucide-react";

const STORAGE_KEY = "sacoparents_court_ordered_case_id";

function readCaseId() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw && raw.trim() ? raw.trim() : null;
  } catch {
    return null;
  }
}

function clearCaseId() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* best-effort */
  }
}

export default function CourtOrderedCaseBadge() {
  const [caseId, setCaseId] = useState(readCaseId);

  useEffect(() => {
    // Also react to same-tab localStorage writes (JoinCode setting
    // the id right before navigating). A storage event only fires
    // cross-tab, so we do a one-shot re-read on mount.
    setCaseId(readCaseId());
  }, []);

  if (!caseId) return null;

  const dismiss = () => {
    clearCaseId();
    setCaseId(null);
  };

  return (
    <div
      className="mt-4 max-w-4xl mx-auto rounded-2xl border border-[#B7E0E0] bg-[#E4F3F3] px-5 py-3 flex items-center justify-between gap-4 flex-wrap"
      data-testid="dashboard-court-ordered-badge"
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-full bg-[#0E7A7A] text-white grid place-items-center flex-shrink-0">
          <Scale size={16} strokeWidth={2.2} />
        </div>
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#0E7A7A]">
            Your court-ordered case
          </div>
          <div className="text-sm text-[#1A1330] mt-0.5 truncate">
            Continue case{" "}
            <strong data-testid="dashboard-court-ordered-badge-id">
              {caseId}
            </strong>{" "}
            — required steps and status.
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Link
          to={`/case/${encodeURIComponent(caseId)}`}
          data-testid="dashboard-court-ordered-badge-link"
          className="inline-flex items-center gap-1.5 rounded-full bg-[#0E7A7A] hover:bg-[#0B5F5F] text-white px-4 py-2 text-sm font-semibold transition-colors"
        >
          Open case
          <ArrowRight size={14} />
        </Link>
        <button
          type="button"
          onClick={dismiss}
          data-testid="dashboard-court-ordered-badge-dismiss"
          aria-label="Dismiss court-ordered case badge"
          className="w-8 h-8 rounded-full hover:bg-white/60 text-[#0E7A7A] grid place-items-center transition-colors"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
