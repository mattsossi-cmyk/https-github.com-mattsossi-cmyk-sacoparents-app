import React, { useState } from "react";
import {
  ChevronDown, ChevronRight as ChevronRightIcon, Sparkles, Ruler,
} from "lucide-react";

/**
 * ReportProvenanceFooter — a small, honest "how this report was built"
 * disclosure at the bottom of every generated report.
 *
 * Distinguishes:
 *   RULE-BASED       — deterministic scoring from your rated answers
 *   GENERATIVE       — parts drafted with technology assistance (Claude)
 *
 * Collapsed by default so it never dominates the report. When open it
 * lists each section against its origin. Sections default to a
 * sensible schema per report type — callers may override.
 */
const RULE_ICON = Ruler;
const GEN_ICON = Sparkles;

const DEFAULTS = {
  mediation: [
    { section: "Goals · issues · priorities capture", origin: "rule" },
    { section: "Communication + readiness scoring", origin: "rule" },
    { section: "Executive summary paragraph", origin: "generative" },
    { section: "Neutral draft agreement wording", origin: "generative" },
    { section: "Personal growth plan phrasing", origin: "generative" },
  ],
  snc: [
    { section: "Areas of need identification", origin: "rule" },
    { section: "Category status (Strength / Developing / …)", origin: "rule" },
    { section: "Recommended co-parenting structure", origin: "rule" },
    { section: "Report introduction paragraph", origin: "generative" },
    { section: "Co-parenting strengths + challenges wording", origin: "generative" },
    { section: "Child impact summary phrasing", origin: "generative" },
  ],
  deepdive: [
    { section: "Section-level flag detection (concern / strength)", origin: "rule" },
    { section: "Overall risk signal aggregation", origin: "rule" },
    { section: "Section coach card (\"Ask the coach\") — where visible", origin: "generative" },
    { section: "Final child-focused summary paragraph", origin: "generative" },
  ],
  comparison: [
    { section: "Alignment scoring per item (aligned / close / divergent)", origin: "rule" },
    { section: "Shared priorities / discussion points / mediation questions grouping", origin: "rule" },
    { section: "Overall alignment percentage", origin: "rule" },
    { section: "Written summary paragraph — where present", origin: "generative" },
  ],
};

/**
 * @param variant  one of "mediation" | "snc" | "deepdive" | "comparison"
 * @param entries  optional overrides — array of {section, origin} where origin ∈ {"rule","generative"}
 */
export default function ReportProvenanceFooter({
  variant = "mediation",
  entries,
  className = "",
}) {
  const [open, setOpen] = useState(false);
  const rows = entries || DEFAULTS[variant] || DEFAULTS.mediation;
  const ruleCount = rows.filter((r) => r.origin === "rule").length;
  const genCount = rows.filter((r) => r.origin === "generative").length;

  return (
    <section
      className={`rounded-2xl border border-[#E5E0EE] bg-white ${className}`}
      data-testid="report-provenance-footer"
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-start gap-3 p-4 sm:p-5 text-left"
        data-testid="report-provenance-toggle"
        aria-expanded={open}
      >
        <div className="shrink-0 h-8 w-8 rounded-full bg-[#F5F1FB] flex items-center justify-center text-[#3D1A78]">
          <RULE_ICON size={14} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
            How this report was built
          </div>
          <div className="text-sm text-[#4B4567] mt-0.5">
            {ruleCount} rule-based section{ruleCount === 1 ? "" : "s"} · {genCount} technology-assisted section{genCount === 1 ? "" : "s"}.
            {" "}Tap for the breakdown.
          </div>
        </div>
        <div className="shrink-0 text-[#3D1A78] mt-1">
          {open ? <ChevronDown size={16} /> : <ChevronRightIcon size={16} />}
        </div>
      </button>

      {open && (
        <div className="px-4 sm:px-5 pb-5" data-testid="report-provenance-body">
          <div className="rounded-xl border border-[#E5E0EE] bg-[#FCFBFE] p-4">
            <ul className="space-y-2.5">
              {rows.map((r) => (
                <li
                  key={`${r.origin}::${r.section}`}
                  className="flex items-start gap-2.5 text-sm"
                  data-testid={`report-provenance-row-${r.origin}`}
                >
                  {r.origin === "rule" ? (
                    <RULE_ICON size={14} className="shrink-0 mt-0.5 text-[#1F5C3B]" aria-hidden />
                  ) : (
                    <GEN_ICON size={14} className="shrink-0 mt-0.5 text-[#8A6B12]" aria-hidden />
                  )}
                  <div className="flex-1">
                    <span className="text-[#1A1330]">{r.section}</span>
                  </div>
                  <span
                    className={`shrink-0 text-[0.625rem] uppercase tracking-[0.14em] font-bold px-2 py-0.5 rounded-full border ${
                      r.origin === "rule"
                        ? "bg-[#F1F9F4] text-[#1F5C3B] border-[#B5DFC5]"
                        : "bg-[#FFF9EB] text-[#8A6B12] border-[#E4D8B8]"
                    }`}
                  >
                    {r.origin === "rule" ? "Rule-based" : "Generative"}
                  </span>
                </li>
              ))}
            </ul>
            <p className="text-[0.6875rem] text-[#6E6787] mt-4 leading-relaxed">
              Rule-based sections are deterministic — the same answers always
              produce the same output. Generative sections are drafted with
              technology assistance (Claude, via a neutral, child-focused
              prompt). You remain responsible for reviewing every part of the
              report before sharing it.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
