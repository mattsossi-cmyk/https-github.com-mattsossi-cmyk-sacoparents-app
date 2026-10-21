import React from "react";

import { JOURNEY_PATHS } from "../../lib/journeyPaths";

// Radio-style list of the three paths; shared by the sign-in picker and Account.
export function PathChoiceList({ value, onChoose, disabled = false, testid = "path-choice" }) {
  return (
    <div role="radiogroup" aria-label="Your path" className="space-y-2" data-testid={testid}>
      {JOURNEY_PATHS.map((p) => {
        const on = value === p.key;
        return (
          <button
            key={p.key}
            type="button"
            role="radio"
            aria-checked={on}
            disabled={disabled}
            onClick={() => onChoose(p.key)}
            data-testid={`${testid}-${p.key}`}
            className={`w-full text-left rounded-2xl border-2 p-3 flex items-center gap-3 transition-colors disabled:opacity-60 ${on ? "border-[#4a2574] bg-[#F5F1FB]" : "border-purple-200 bg-white hover:bg-purple-50"}`}
          >
            <span className="shrink-0 w-10 h-10 rounded-xl bg-purple-100 text-purple-700 grid place-items-center" aria-hidden="true">
              <i className={`fa-solid ${p.icon}`}></i>
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-bold text-slate-900">{p.label}</span>
              <span className="block text-[0.6875rem] text-purple-700 leading-snug">{p.detail}</span>
            </span>
            {on && <i className="fa-solid fa-circle-check text-[#4a2574]" aria-hidden="true"></i>}
          </button>
        );
      })}
    </div>
  );
}
