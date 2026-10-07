import React from "react";

import { CONTENT } from "./content";

// Personal Co-Parenting Goal — shown on the dashboard until the next Self-Assessment.
export function GoalBanner({ goal, setAt, onOpen, testid }) {
  if (!goal) return null;
  const when = setAt
    ? new Date(setAt).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    : null;
  return (
    <section
      data-testid={testid}
      className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-4 shadow-sm"
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center">
          <i className="fa-solid fa-bullseye"></i>
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase font-bold tracking-wider text-emerald-800">{CONTENT.goal.label}</div>
          <p data-testid={`${testid}-text`} className="text-sm font-semibold text-slate-900 leading-snug mt-0.5 break-words">
            {goal}
          </p>
          {when && <p className="text-[10px] text-slate-500 mt-1">Set {when}</p>}
        </div>
      </div>
      <button
        type="button"
        data-testid={`${testid}-open`}
        onClick={onOpen}
        className="mt-3 w-full py-2 rounded-full bg-white hover:bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs font-bold transition-colors"
      >
        <i className="fa-solid fa-chart-line mr-1.5"></i>
        See my progress or reassess
      </button>
    </section>
  );
}
