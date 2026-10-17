/**
 * CourtReportDisclaimer.jsx — a shared block that must appear next to
 * every court-facing PDF or on-screen surface in the app.
 *
 * Added 2026-03-06 following the product review's guardrail:
 * "Any court-facing document should clearly state: who completed it;
 * whether answers were verified; whether both parents participated;
 * that the report is not a custody evaluation; that scores are not
 * clinical findings; that no recommendation determines the child's
 * best interest."
 *
 * Two variants:
 *   - full   (default) — six-bullet block for the top of a report
 *                        view or download-and-share page.
 *   - inline           — one-line summary next to a "Download" button.
 */
import React from "react";
import { Info, ShieldAlert } from "lucide-react";

const BULLETS = [
  {
    key: "author",
    text: (name) =>
      name
        ? `Completed by ${name} — the parent named above filled in every answer themselves.`
        : "Completed by the parent named above — they filled in every answer themselves.",
  },
  {
    key: "unverified",
    text: () =>
      "Answers are self-reported and not verified by a licensed clinician, court officer, or independent evaluator.",
  },
  {
    key: "participation",
    text: (name, both) =>
      both
        ? "Both parents participated — this is a joint reflection built from two separate private inputs."
        : "Only one parent completed this reflection — the other parent's perspective is not included.",
  },
  {
    key: "not-evaluation",
    text: () =>
      "This is not a custody evaluation and is not intended to replace one.",
  },
  {
    key: "not-clinical",
    text: () =>
      "Scores and dimensions are educational reflections — they are not clinical findings, diagnoses, or risk determinations.",
  },
  {
    key: "not-best-interest",
    text: () =>
      "Nothing in this document is a recommendation about the child's best interest. Best-interest decisions are for the parents, their professionals, and — where appropriate — the court.",
  },
];

export default function CourtReportDisclaimer({
  variant = "full",
  authorName = null,
  bothParents = false,
  className = "",
  testId = "court-report-disclaimer",
}) {
  if (variant === "inline") {
    return (
      <div
        className={`inline-flex items-start gap-2 rounded-full border border-[#F1D9B7] bg-[#FFF6EA] px-3 py-1.5 text-[0.6875rem] text-[#5A3C10] ${className}`}
        data-testid={`${testId}-inline`}
      >
        <Info size={12} className="mt-0.5 shrink-0" />
        <span>
          Educational, parent-reported, not a custody evaluation — full
          disclaimers inside the report.
        </span>
      </div>
    );
  }
  return (
    <section
      className={`rounded-2xl border-2 border-[#F1D9B7] bg-[#FFF6EA] p-5 ${className}`}
      data-testid={testId}
      role="note"
      aria-label="Court report disclaimer"
    >
      <div className="flex items-center gap-2 mb-3">
        <ShieldAlert size={16} className="text-[#8A4610]" />
        <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#8A4610]">
          Before this document is used in a court, mediation, or legal setting
        </div>
      </div>
      <ul className="grid gap-2 text-[0.8125rem] text-[#5A3C10] leading-relaxed">
        {BULLETS.map((b) => (
          <li key={b.key} className="flex gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[#8A4610] shrink-0" />
            <span>{b.text(authorName, bothParents)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
