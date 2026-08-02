import React from "react";
import { AlertCircle } from "lucide-react";

/**
 * ReportReviewNotice — a small, high-contrast disclaimer that appears
 * near the top of every generated report.
 *
 *   variant="individual" (default) — for single-parent reports.
 *   variant="comparison"           — for two-parent compare reports.
 *
 * The wording is intentionally neutral and short. It exists so parents,
 * mediators, and any third party who receives the PDF understand what
 * the report is (and, importantly, isn't).
 */
export default function ReportReviewNotice({ variant = "individual", className = "" }) {
  const body = variant === "comparison"
    ? "This report organizes both parents' reported perspectives side-by-side. It does not determine which account is correct. Review it carefully with your co-parent, mediator, or attorney before relying on it."
    : "Review this report carefully before sharing it. It reflects one parent's responses and has not been independently verified.";
  return (
    <aside
      role="note"
      data-testid={`report-review-notice-${variant}`}
      className={`rounded-2xl border border-[#E4D8B8] bg-[#FFF9EB] p-4 sm:p-5 flex items-start gap-3 ${className}`}
    >
      <AlertCircle size={18} className="shrink-0 mt-0.5 text-[#8A6B12]" aria-hidden />
      <div>
        <div className="text-[10px] uppercase tracking-[0.22em] text-[#8A6B12] font-bold">
          Please review before sharing
        </div>
        <p className="text-sm sm:text-[15px] text-[#3B2A05] leading-relaxed mt-1.5">
          {body}
        </p>
      </div>
    </aside>
  );
}
