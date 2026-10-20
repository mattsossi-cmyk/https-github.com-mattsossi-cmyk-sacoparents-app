/**
 * PathwayReportCard — Compact preview of the Dispute Resolution
 * Pathway Report for the Dashboard. Hits `/pathway-report/preview`
 * and self-hides for parents who have no Safety / Companion / ND Risk
 * data on file yet (nothing meaningful to recommend from).
 *
 * When shown, surfaces:
 *   - Primary pathway label (from the deterministic rule engine)
 *   - Suitability tone chip (safe / stretched / hard-locked)
 *   - "Single-parent preview" tag so parents don't mistake the card
 *     for the full two-parent report
 *   - A red "Safety trigger applied" tag when the algorithm hard-
 *     locked away from a consensual process
 *   - CTA linking to the full report at `/pathway-report`
 *
 * Language matches the report page itself: never says "you should",
 * always frames as "the assessment data indicates".
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Scale, ShieldAlert, ArrowRight } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";


// Any parent input on file counts as "enough data to render a preview".
// If literally nothing is on file, the card hides entirely so the
// dashboard is not cluttered for first-time visitors.
function hasAnyInputs(data) {
  const p = data?.data_inputs_present || {};
  return !!(p.dimension_companion || p.nd_risk || p.compliance);
}


export default function PathwayReportCard() {
  const [state, setState] = useState({ loading: true, data: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/pathway-report/preview");
        if (!cancelled) setState({ loading: false, data });
      } catch (err) {
        logError("PathwayReportCard preview", err);
        if (!cancelled) setState({ loading: false, data: null });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Hide while loading + when the parent has nothing to preview yet.
  if (state.loading || !state.data || !hasAnyInputs(state.data)) return null;

  const d = state.data;
  const hardLocked = (d.hard_locked_by || []).length > 0;
  const label = d.primary_pathway_label || "Pathway recommendation";
  const summary = d.primary_pathway_summary || "";

  return (
    <Link
      to="/pathway-report"
      className={
        "block rounded-3xl border p-5 transition-shadow hover:shadow-md " +
        (hardLocked
          ? "border-[#EFB4B4] bg-[#FCEDEB] hover:border-[#B02A2A]"
          : "border-[#E5E0EE] bg-white hover:border-[#3D1A78]")
      }
      data-testid="pathway-report-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="inline-flex items-center gap-2 min-w-0">
          <span
            className="inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0"
            style={{
              background: hardLocked ? "#B02A2A" : "#3D1A78",
              color: "#FFFFFF",
            }}
          >
            {hardLocked ? <ShieldAlert size={16} /> : <Scale size={16} />}
          </span>
          <div className="min-w-0">
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Dispute Resolution · Pathway
            </div>
            <div className="font-serif text-lg text-[#1A1330] leading-snug truncate"
              data-testid="pathway-report-card-label">
              {label}
            </div>
          </div>
        </div>
        <span
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[0.625rem] uppercase tracking-[0.16em] font-bold shrink-0"
          style={{
            background: hardLocked ? "#F8D7D7" : "#F0EEF8",
            color:      hardLocked ? "#7A1A1A" : "#3D1A78",
          }}
          data-testid="pathway-report-card-scope"
        >
          {d.is_dual_party ? "Two-parent" : "Preview"}
        </span>
      </div>

      {summary && (
        <p className="text-sm text-[#4B4567] mt-3 leading-relaxed line-clamp-2"
          data-testid="pathway-report-card-summary">
          {summary}
        </p>
      )}

      {hardLocked && (
        <div
          className="mt-3 inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[0.6875rem] font-bold bg-white/70 text-[#B02A2A] border border-[#EFB4B4]"
          data-testid="pathway-report-card-hard-lock"
        >
          <ShieldAlert size={11} />
          Safety trigger applied
        </div>
      )}

      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-[0.6875rem] text-[#4B4567] italic">
          {d.is_dual_party
            ? "Both parents have consented via Compare Share."
            : "Single-parent preview. Invite your co-parent to unlock the full report."}
        </span>
        <span className="inline-flex items-center gap-1 text-[0.6875rem] font-bold text-[#3D1A78]"
          data-testid="pathway-report-card-cta">
          View full report <ArrowRight size={12} />
        </span>
      </div>
    </Link>
  );
}
