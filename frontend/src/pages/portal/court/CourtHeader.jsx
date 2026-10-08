import React from "react";

export const AI_GRADIENT = "linear-gradient(135deg, #4a148c 0%, #7b2cbf 50%, #3a86ff 100%)";

export function CourtHeader({ onBack, onQuickExit, hints, onToggleHints }) {
  return (
    <header
      data-testid="court-header"
      className="flex flex-wrap justify-between items-center gap-3 bg-white px-4 sm:px-5 py-3.5 rounded-2xl shadow-[0_4px_15px_rgba(59,21,102,0.08)] mb-5"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <button
          type="button"
          data-testid="court-back"
          onClick={onBack}
          aria-label="Back to dashboard"
          className="shrink-0 w-9 h-9 rounded-full bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566] flex items-center justify-center transition-colors"
        >
          <i className="fa-solid fa-arrow-left"></i>
        </button>
        <span data-testid="court-logo" className="font-extrabold text-[#3b1566] text-[1.1rem] flex items-center gap-2 whitespace-nowrap">
          <i className="fa-solid fa-scale-balanced"></i> SA CoParents Path
        </span>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          data-testid="court-hints-toggle"
          aria-pressed={hints}
          onClick={onToggleHints}
          className="bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566] border border-[#e7dbf8] px-3.5 py-2 rounded-full text-[0.85rem] font-semibold flex items-center gap-1.5 transition-colors"
        >
          <i className={`fa-solid ${hints ? "fa-eye" : "fa-eye-slash"}`}></i>
          <span>{hints ? "Hide Hints" : "Show Hints"}</span>
        </button>
        <span
          data-testid="court-ai-badge"
          className="text-white px-3.5 py-1.5 rounded-full text-[0.82rem] font-bold flex items-center gap-1.5"
          style={{ background: AI_GRADIENT }}
        >
          <i className="fa-solid fa-wand-magic-sparkles"></i> Emergent AI
        </span>
        <button
          type="button"
          data-testid="court-quick-exit"
          onClick={onQuickExit}
          className="px-3 py-2 rounded-full text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors whitespace-nowrap"
        >
          <i className="fa-solid fa-bolt mr-1.5"></i>Quick Exit
        </button>
      </div>
    </header>
  );
}
