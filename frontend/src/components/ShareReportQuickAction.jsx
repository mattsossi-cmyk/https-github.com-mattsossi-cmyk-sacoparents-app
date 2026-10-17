import React from "react";
import { Link } from "react-router-dom";
import { Share2, ArrowRight, Lock, FileText, Handshake } from "lucide-react";

import {
  jointReportUrl,
  jointAgreementUrl,
} from "../lib/jointArtefactUrls";

/**
 * "Share a report" quick-action row for the Dashboard hero.
 *
 * Behaviour:
 *   - If the parent has a ready Compare share (sncHighlights.ready &&
 *     sncHighlights.share_id), two pills render side-by-side: one that
 *     routes straight into the Joint Report mint dialog, one that
 *     routes into the Joint Agreement mint dialog. Both use `?mint=1`
 *     so the target page auto-opens its "Create shareable link"
 *     dialog once the report/agreement finishes loading.
 *   - Otherwise a single soft-locked pill explains what's needed to
 *     unlock, without hiding the entry point.
 *
 * Placed inside the Step 1 hero card so parents see it above the fold
 * on every dashboard visit, but styled small enough that it never
 * competes with the Step 1 question.
 */
export default function ShareReportQuickAction({ sncHighlights }) {
  const ready = Boolean(sncHighlights?.ready && sncHighlights?.share_id);
  const shareId = sncHighlights?.share_id;

  if (!ready) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <div
          className="inline-flex items-center gap-2 rounded-full border border-[#E5E0EE] bg-[#FAF8FD] text-[#4B4567] px-4 py-2 text-xs sm:text-sm font-medium"
          data-testid="dashboard-share-report-quick-action-locked"
          title="Complete the Co-Parenting Assessment with your co-parent to unlock the shared report."
        >
          <Lock size={13} className="opacity-70" />
          <span>Share a report — unlocks after your Compare is ready</span>
        </div>
        <Link
          to="/joint-reports"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] hover:underline"
          data-testid="dashboard-see-all-report-types"
        >
          See all report types →
        </Link>
      </div>
    );
  }

  const encoded = encodeURIComponent(shareId);

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid="dashboard-share-report-quick-actions"
    >
      <span className="inline-flex items-center gap-1.5 text-[0.6875rem] uppercase tracking-[0.14em] font-semibold text-[#3D1A78] mr-1">
        <Share2 size={12} />
        Share
      </span>
      <Link
        to={jointReportUrl(shareId)}
        className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-xs sm:text-sm font-semibold shadow-sm hover:bg-[#2f1360] hover:shadow-md transition-all"
        data-testid="dashboard-share-report-quick-action"
      >
        <FileText size={14} />
        <span>Co-Parenting Agreement</span>
        <ArrowRight size={14} className="opacity-80" />
      </Link>
      <Link
        to={jointAgreementUrl(shareId)}
        className="inline-flex items-center gap-2 rounded-full border border-[#3D1A78] text-[#3D1A78] bg-white px-4 py-2 text-xs sm:text-sm font-semibold shadow-sm hover:bg-[#F1EEF7] hover:shadow-md transition-all"
        data-testid="dashboard-share-agreement-quick-action"
      >
        <Handshake size={14} />
        <span>Joint Alignment Agreement</span>
        <ArrowRight size={14} className="opacity-80" />
      </Link>
      <Link
        to="/joint-reports"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] hover:underline"
        data-testid="dashboard-see-all-report-types"
      >
        See all report types →
      </Link>
    </div>
  );
}
