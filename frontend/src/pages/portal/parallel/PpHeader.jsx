import React from "react";

export function PpHeader({ stepIndex, total, title, onBack, onHome, onQuickExit }) {
  const pct = stepIndex == null ? 0 : Math.round(((stepIndex + 1) / total) * 100);
  return (
    <header data-testid="pp-header" className="bg-white border-b border-purple-100 sticky top-0 z-40 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <button
            type="button"
            data-testid="pp-back"
            onClick={onBack}
            aria-label="Back to Self Journey"
            className="shrink-0 w-9 h-9 rounded-full bg-[#f4f0fa] hover:bg-purple-100 text-[#4a2574] flex items-center justify-center transition-colors"
          >
            <i className="fa-solid fa-arrow-left"></i>
          </button>
          <button type="button" data-testid="pp-home" onClick={onHome} className="flex items-center gap-3 min-w-0 text-left">
            <span className="hidden sm:flex w-10 h-10 rounded-full bg-[#4a2574] items-center justify-center text-white shadow-md">
              <i className="fa-solid fa-users"></i>
            </span>
            <span className="min-w-0">
              <span className="block text-base sm:text-xl font-black tracking-tight text-[#4a2574] whitespace-nowrap">
                SA CoParents<span className="text-xs text-[#8251b8] font-semibold">™</span>
              </span>
              <span className="hidden sm:block text-[10px] uppercase tracking-widest text-gray-500 font-bold -mt-0.5">
                Start With Alignment. End With Agreement.
              </span>
            </span>
          </button>
        </div>
        <div className="flex items-center gap-4">
          {stepIndex != null && (
            <div data-testid="pp-header-progress" className="hidden md:flex items-center gap-4">
              <div className="text-right">
                <span className="text-xs font-semibold uppercase text-[#4a2574]">
                  Step {stepIndex + 1} of {total}
                </span>
                <p className="text-sm font-bold text-gray-800">{title}</p>
              </div>
              <div className="w-32 bg-gray-200 h-2.5 rounded-full overflow-hidden">
                <div className="bg-[#4a2574] h-full transition-[width] duration-300" style={{ width: `${pct}%` }} />
              </div>
            </div>
          )}
          <button
            type="button"
            data-testid="pp-quick-exit"
            onClick={onQuickExit}
            className="shrink-0 px-3 py-2 rounded-lg text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors whitespace-nowrap"
          >
            <i className="fa-solid fa-bolt mr-1.5"></i>Quick Exit
          </button>
        </div>
      </div>
    </header>
  );
}
