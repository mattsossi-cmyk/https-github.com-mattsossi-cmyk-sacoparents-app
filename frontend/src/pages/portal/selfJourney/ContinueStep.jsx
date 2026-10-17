import React from "react";

import { scrollToTestId } from "./FlowArrow";

// "Continue at Step N" button: jumps to the first unfinished Self Journey step.
export function ContinueStep({ step, doneCount, total }) {
  return (
    <button
      type="button"
      data-testid="door-self-continue"
      onClick={() => scrollToTestId(step.to)}
      className="w-full rounded-2xl bg-emerald-500 hover:bg-emerald-600 text-white px-4 sm:px-5 py-3.5 flex items-center gap-3 text-left transition-colors shadow-[0_10px_24px_-12px_rgba(16,185,129,0.8)]"
    >
      <span className="w-10 h-10 rounded-full bg-white text-emerald-600 flex items-center justify-center shrink-0 shadow-sm">
        <i className="fa-solid fa-arrow-down"></i>
      </span>
      <span className="min-w-0 flex-1">
        <span data-testid="door-self-continue-title" className="block text-base font-extrabold leading-tight">
          Continue at Step {step.n}
        </span>
        <span data-testid="door-self-continue-detail" className="block text-[0.75rem] text-emerald-50 leading-snug mt-0.5">
          {step.label} · {doneCount} of {total} steps done
        </span>
      </span>
      <i aria-hidden="true" className="fa-solid fa-chevron-down text-sm"></i>
    </button>
  );
}
