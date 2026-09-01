import React from "react";
import { Link } from "react-router-dom";
import { Share2, ArrowRight, Lock } from "lucide-react";

/**
 * Compact "Share a report" quick-action pill for the Dashboard hero.
 *
 * Behaviour:
 *   - If the parent has a ready Compare share (sncHighlights.ready &&
 *     sncHighlights.share_id) the pill routes straight into the Joint
 *     Professional Report where the "Create shareable link" mint dialog
 *     lives. That is the shortest path from Dashboard → shareable URL.
 *   - Otherwise the pill renders in a soft-locked state that explains
 *     what's needed to unlock, without hiding the entry point.
 *
 * Placed inside the Step 1 hero card so parents see it above the fold
 * on every dashboard visit, but styled small enough that it never
 * competes with the Step 1 question.
 */
export default function ShareReportQuickAction({ sncHighlights }) {
  const ready = Boolean(sncHighlights?.ready && sncHighlights?.share_id);
  const shareId = sncHighlights?.share_id;

  if (ready) {
    return (
      <Link
        to={`/joint-professional-report?share=${encodeURIComponent(shareId)}&mint=1`}
        className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-xs sm:text-sm font-semibold shadow-sm hover:bg-[#2f1360] hover:shadow-md transition-all"
        data-testid="dashboard-share-report-quick-action"
      >
        <Share2 size={14} />
        <span>Share a report with your mediator</span>
        <ArrowRight size={14} className="opacity-80" />
      </Link>
    );
  }

  return (
    <div
      className="inline-flex items-center gap-2 rounded-full border border-[#E5E0EE] bg-[#FAF8FD] text-[#4B4567] px-4 py-2 text-xs sm:text-sm font-medium"
      data-testid="dashboard-share-report-quick-action-locked"
      title="Complete the Co-Parenting Assessment with your co-parent to unlock the shared report."
    >
      <Lock size={13} className="opacity-70" />
      <span>Share a report — unlocks after your Compare is ready</span>
    </div>
  );
}
