/**
 * AlignReportCTA — compact dashboard card that links out to the
 * Align Report tool (a companion Emergent app) for parents who want to
 * create a Shared Parenting Report.
 *
 * Opens in a new tab so parents don't lose their SA CoParents session.
 * Deliberately compact so it doesn't compete with the primary Do-This-
 * Next / Your-Progress / Your-Reports above-the-fold blocks.
 */
import React from "react";
import { ExternalLink, Users } from "lucide-react";

const ALIGN_REPORT_URL = "https://align-report.emergent.host/";

export default function AlignReportCTA() {
  return (
    <a
      href={ALIGN_REPORT_URL}
      target="_blank"
      rel="noopener noreferrer"
      data-testid="align-report-cta"
      className="group flex items-center gap-3 rounded-3xl border border-[#E5E0EE] bg-gradient-to-r from-[#F5F1FB] to-[#EAF7F7] p-4 sm:p-5 hover:border-[#3D1A78] hover:shadow-md transition-all"
    >
      <div
        className="shrink-0 h-11 w-11 rounded-full grid place-items-center bg-white text-[#3D1A78]"
        aria-hidden
      >
        <Users size={18} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
          Companion tool
        </div>
        <div className="text-sm sm:text-base font-semibold text-[#1A1330] mt-0.5 leading-tight">
          Create a Shared Parenting Report
        </div>
        <div className="text-xs text-[#4B4567] mt-1 leading-relaxed">
          Compare two parents&rsquo; answers side-by-side and generate a
          neutral shared report. Opens in a new tab.
        </div>
      </div>
      <span
        className="shrink-0 inline-flex items-center gap-1 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold group-hover:bg-[#3D1A78] group-hover:text-white transition-colors"
        data-testid="align-report-cta-btn"
      >
        Open <ExternalLink size={11} strokeWidth={2.4} />
      </span>
    </a>
  );
}
