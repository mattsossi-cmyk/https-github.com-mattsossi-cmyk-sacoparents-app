/**
 * PathwayReportPrompt — small CTA card shown on any active Compare share.
 *
 * Deep-links into the Dispute Resolution Pathway Report page in
 * *dual-party* mode using the caller's active share_id. The backend
 * endpoint (`/pathway-report/dual/{share_id}`) enforces:
 *   - Share exists
 *   - Share status == "active" (both parents already consented)
 *   - Caller is a participant
 * So this button is safe to show anywhere a Compare view successfully
 * rendered (that context is by construction post-consent).
 *
 * Copy is deliberately conservative — matches the language guardrails
 * of the pathway report itself: "for professional consideration",
 * never "your recommended pathway".
 */
import React from "react";
import { Link } from "react-router-dom";
import { Scale, ChevronRight } from "lucide-react";


export default function PathwayReportPrompt({ shareId, testidPrefix = "compare" }) {
  if (!shareId) return null;
  return (
    <section
      className="mt-5 rounded-3xl border border-[#D6CFE8] bg-gradient-to-br from-[#F5F1FB] to-white p-5 sm:p-6 shadow-sm"
      data-testid={`${testidPrefix}-pathway-report-prompt`}
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className="shrink-0 h-9 w-9 rounded-full bg-[#3D1A78] text-white grid place-items-center">
            <Scale size={16} />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Dispute Resolution Pathway Report
            </div>
            <div className="font-serif text-xl text-[#1A1330] leading-snug mt-1">
              Both parents have consented — generate the two-parent pathway report
            </div>
            <p className="text-sm text-[#4B4567] mt-2 max-w-2xl leading-relaxed">
              Combines this compare with both parents&apos; Safety Screen,
              Companion, and ND Risk data to identify which dispute
              resolution pathway warrants professional consideration —
              Mediation, Child-Centered Relational Mediation, Collaborative
              Law, or court intervention. Includes suitability ratings,
              factors, and goals for each pathway.
            </p>
          </div>
        </div>
        <Link
          to={`/pathway-report?share=${encodeURIComponent(shareId)}`}
          data-testid={`${testidPrefix}-pathway-report-open`}
          className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-2 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all shrink-0"
        >
          Generate report <ChevronRight size={14} />
        </Link>
      </div>
    </section>
  );
}
