/**
 * SituationPickerHero.jsx — the "What best describes your situation?"
 * card that opens the Dashboard.
 *
 * Extracted from Dashboard.jsx (2026-03-05) so the main Dashboard file
 * stays a shell orchestrator and the picker's data + rendering live
 * together in one small file. State (which situation the parent chose,
 * whether they want to reset it) is kept in Dashboard.jsx because the
 * choice is also used to highlight recommended prep modules in a
 * downstream card.
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  Handshake,
  MessageCircle,
  AlertTriangle,
  ShieldCheck,
  Baby,
  Scale,
} from "lucide-react";

import ShareReportQuickAction from "../ShareReportQuickAction";

// Six situations that route the visitor to the safest / most relevant
// next step. Mirrors the language and order used on the Landing page so
// pre- and post-signup experiences feel identical.
export const INLINE_SITUATIONS = [
  {
    key: "cooperate",
    label: "We generally cooperate",
    icon: <Handshake size={18} />,
    route: "#next-step",
  },
  {
    key: "difficult",
    label: "Communication is difficult",
    icon: <MessageCircle size={18} />,
    route: "#next-step",
  },
  {
    key: "high-conflict",
    label: "We experience ongoing high conflict",
    icon: <AlertTriangle size={18} />,
    route: "/safety-assessment",
  },
  {
    key: "safety",
    label: "I have safety or family-violence concerns",
    icon: <ShieldCheck size={18} />,
    route: "/safety-assessment",
  },
  {
    key: "special-needs",
    label: "Our child has unique educational, psychological or medical needs",
    icon: <Baby size={18} />,
    route: "/special-needs-v2",
  },
  {
    key: "mediation",
    label: "I am preparing for mediation or court",
    icon: <Scale size={18} />,
    route: "#next-step",
  },
];

export default function SituationPickerHero({
  userName,
  situationChoice,
  onRemember,
  onForget,
  sncHighlights,
}) {
  return (
    <div
      className="mt-4 rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm"
      data-testid="dashboard-step1-hero"
    >
      <div className="text-[0.6875rem] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">
        Step 1
      </div>
      <h1
        className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight"
        data-testid="dashboard-greeting"
      >
        What best describes your situation
        {userName ? `, ${userName.split(" ")[0]}?` : "?"}
      </h1>
      {/* Quick action — shortest path from Dashboard to a shareable
          Joint Report link. Soft-locked until the Compare share is
          ready so it never sends a parent to an empty state. */}
      <div className="mt-4">
        <ShareReportQuickAction sncHighlights={sncHighlights} />
      </div>
      {situationChoice ? (
        <div
          className="mt-4 flex items-center gap-3 flex-wrap"
          data-testid="dashboard-situation-remembered"
        >
          <div className="inline-flex items-center gap-2 rounded-full bg-[#EFE9F9] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold">
            {(() => {
              const meta = INLINE_SITUATIONS.find(
                (s) => s.key === situationChoice,
              );
              return meta ? (
                <>
                  {meta.icon}
                  <span>You chose: {meta.label}</span>
                </>
              ) : (
                <span>Situation remembered</span>
              );
            })()}
          </div>
          <button
            type="button"
            onClick={onForget}
            className="text-xs text-[#4B4567] hover:text-[#3D1A78] hover:underline"
            data-testid="dashboard-situation-reset"
          >
            Change my answer
          </button>
        </div>
      ) : (
        <>
          <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-2xl">
            There are no wrong answers. Your choice routes you straight
            to the safest and most relevant next step for your family.
          </p>
          <div
            className="mt-5 grid sm:grid-cols-2 gap-2.5"
            data-testid="dashboard-situation-inline-picker"
          >
            {INLINE_SITUATIONS.map((s) => (
              <Link
                key={s.key}
                to={s.route}
                onClick={() => onRemember(s.key)}
                className="group text-left rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#F7F4FC] transition-colors flex items-center gap-3"
                data-testid={`dashboard-situation-${s.key}`}
              >
                <div className="shrink-0 w-9 h-9 rounded-full bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center group-hover:bg-[#3D1A78] group-hover:text-white transition-colors">
                  {s.icon}
                </div>
                <span className="text-sm sm:text-[15px] text-[#1A1330] leading-snug">
                  {s.label}
                </span>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
