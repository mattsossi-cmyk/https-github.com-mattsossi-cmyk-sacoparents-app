import React from "react";

import { ASSESS_ORDER, ASSESS_NAMES } from "./selfJourneyArt";

const R = 22;
const C = 2 * Math.PI * R;

// "X of 5 assessments done" ring; tapping it opens the next unfinished assessment.
export function AssessProgressRing({ done, onOpen }) {
  const count = ASSESS_ORDER.filter((k) => done[k]).length;
  const next = ASSESS_ORDER.find((k) => !done[k]);
  const color = next ? "#6b2fb3" : "#2f9e44";
  return (
    <button
      type="button"
      data-testid="door-self-progress-ring"
      data-done={count}
      disabled={!next}
      onClick={() => onOpen(next)}
      className="w-full flex items-center gap-3 bg-white border border-purple-100 rounded-2xl px-4 py-3 shadow-sm text-left transition-[box-shadow,border-color] hover:shadow-md hover:border-purple-300 disabled:hover:shadow-sm disabled:hover:border-purple-100 disabled:cursor-default"
    >
      <span className="relative shrink-0 w-14 h-14">
        <svg width="56" height="56" viewBox="0 0 56 56" className="-rotate-90" aria-hidden="true">
          <circle cx="28" cy="28" r={R} stroke="#ede4fb" strokeWidth="6" fill="none" />
          <circle
            cx="28"
            cy="28"
            r={R}
            stroke={color}
            strokeWidth="6"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={C}
            strokeDashoffset={C * (1 - count / ASSESS_ORDER.length)}
            className="transition-[stroke-dashoffset] duration-700 ease-out"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-[13px] font-extrabold text-[#3b1566]">
          {count}/{ASSESS_ORDER.length}
        </span>
      </span>
      <span className="min-w-0 flex-1">
        <span data-testid="door-self-progress-count" className="block text-sm font-extrabold text-[#3b1566] leading-tight">
          {count} of {ASSESS_ORDER.length} assessments done
        </span>
        <span data-testid="door-self-progress-next" className="block text-[11px] text-slate-600 mt-0.5 leading-snug">
          {next ? (
            <>
              Next: <span className="font-semibold text-purple-800">{ASSESS_NAMES[next]}</span>
            </>
          ) : (
            "All five done. Wonderful work for your child."
          )}
        </span>
      </span>
      {next ? (
        <span className="shrink-0 w-8 h-8 rounded-full bg-[#6b2fb3] text-white flex items-center justify-center">
          <i className="fa-solid fa-chevron-right text-xs"></i>
        </span>
      ) : (
        <i className="fa-solid fa-circle-check text-2xl text-[#2f9e44] shrink-0"></i>
      )}
    </button>
  );
}
