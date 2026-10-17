import React from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  ArrowRight,
  Sparkles,
} from "lucide-react";

import { jointReportUrl } from "../lib/jointArtefactUrls";

/**
 * AssessmentHistoryCard — the third access point for the Co-Parenting
 * Agreement per the walkthrough.
 *
 * Renders a compact table of every prep module the parent has completed.
 * Each row exposes:
 *   - The module label (parent-facing)
 *   - A soft "Completed" chip
 *   - A right-side action:
 *       • If a ready Compare share exists → "View Co-Parenting Agreement →"
 *         (routed with ?mint=1 so a single tap lands in the mint dialog)
 *       • Otherwise → a subtle "Review" link back to the module route
 *
 * Data source: `prep.completed` (from `/mediation/prep`) — already fetched
 * by the parent Dashboard, so this component is data-driven, not
 * fetch-driven. Zero new network calls.
 */
export default function AssessmentHistoryCard({
  steps,
  completed,
  sncHighlights,
  testidPrefix = "assessment-history",
}) {
  const completedSteps = (steps || []).filter((s) => completed?.[s.key]);
  if (completedSteps.length === 0) return null;

  const ready = Boolean(sncHighlights?.ready && sncHighlights?.share_id);
  const shareId = sncHighlights?.share_id;

  return (
    <div
      className="card-soft p-6 sm:p-7"
      data-testid={`${testidPrefix}-card`}
    >
      <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
        <div>
          <div className="eyebrow text-[#3D1A78]">Assessment History</div>
          <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight mt-1">
            What you've completed so far
          </h3>
          <p className="text-xs text-[#4B4567] mt-1 max-w-lg">
            Every finished module is here — tap any row to jump back in, or
            open the Co-Parenting Agreement next to the modules your co-parent
            has finished too.
          </p>
        </div>
        {ready && (
          <span
            className="inline-flex items-center gap-1.5 text-[0.6875rem] uppercase tracking-[0.14em] font-bold text-[#1F5C3B] bg-[#EAF7F0] border border-[#C6DECF] rounded-full px-2.5 py-1 shrink-0"
            data-testid={`${testidPrefix}-report-ready-chip`}
          >
            <Sparkles size={11} /> Joint Report ready
          </span>
        )}
      </div>

      <ul
        className="divide-y divide-[#EFECF6] rounded-2xl border border-[#EFECF6] bg-white"
        data-testid={`${testidPrefix}-list`}
      >
        {completedSteps.map((s) => {
          const Icon = s.icon;
          return (
            <li
              key={s.key}
              className="flex items-center gap-3 px-4 py-3 sm:px-5 sm:py-4"
              data-testid={`${testidPrefix}-row-${s.key}`}
            >
              <div className="w-9 h-9 rounded-xl bg-[#F1EEF7] grid place-items-center text-[#3D1A78] shrink-0">
                {Icon ? <Icon size={16} /> : <CheckCircle2 size={16} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-[#1A1330] text-sm truncate">
                  {s.label}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="inline-flex items-center gap-1 text-[0.625rem] uppercase tracking-[0.14em] font-semibold text-[#1F5C3B]">
                    <CheckCircle2 size={10} />
                    Completed
                  </span>
                </div>
              </div>
              <div className="shrink-0 flex items-center gap-3">
                {ready ? (
                  <Link
                    to={jointReportUrl(shareId)}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-[#3D1A78] hover:underline"
                    data-testid={`${testidPrefix}-view-report-${s.key}`}
                  >
                    View Co-Parenting Agreement
                    <ArrowRight size={12} />
                  </Link>
                ) : (
                  <Link
                    to={s.path || "/dashboard"}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-[#6E6787] hover:text-[#3D1A78] hover:underline"
                    data-testid={`${testidPrefix}-review-${s.key}`}
                  >
                    Review
                    <ArrowRight size={12} />
                  </Link>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {!ready && (
        <p
          className="text-[0.6875rem] text-[#6E6787] mt-3"
          data-testid={`${testidPrefix}-waiting-hint`}
        >
          Invite your co-parent to see a Co-Parenting Agreement link appear
          next to each row.
        </p>
      )}
    </div>
  );
}
