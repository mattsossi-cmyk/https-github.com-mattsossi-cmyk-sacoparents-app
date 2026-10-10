import React from "react";

import CONTENT from "../childNeedsContent.json";
import { SentToList } from "./SentToList";

const CATS = Object.fromEntries(CONTENT.categories.map((c) => [c.key, c]));

function StatusChip({ k, done, draft, active, onPick }) {
  const [text, tone] = done ? ["Completed ✓", "text-emerald-700 bg-emerald-50 border-emerald-200"] : draft ? ["Draft saved", "text-amber-700 bg-amber-50 border-amber-200"] : ["Not started", "text-slate-500 bg-slate-50 border-slate-200"];
  return (
    <button type="button" data-testid={`child-needs-progress-${k}`} onClick={() => onPick(k)} className={`w-full flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-colors hover:border-[#611663] ${active ? "ring-2 ring-[#4A154B]/30" : ""} ${tone}`}>
      <span className="text-[13px] font-semibold text-slate-800">{CATS[k].card_title}</span>
      <span className="text-[11px] font-bold whitespace-nowrap">{text}</span>
    </button>
  );
}

// End-of-page accomplishments: forms completed, who it was sent to, and the report download.
export function NeedsProgress({ order, done, drafts, activeKey, onPick, shares, showSent, onDownload }) {
  const count = order.filter((k) => done[k]).length;
  return (
    <section data-testid="child-needs-progress" className="bg-white rounded-xl border border-[#E2E8F0] shadow-[0_10px_15px_-3px_rgba(0,0,0,0.05)] p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h3 className="text-base font-extrabold text-[#4A154B]">Your progress</h3>
        <span data-testid="child-needs-progress-count" className="text-[12px] font-bold text-[#4A154B] bg-[#F4EEF5] rounded-full px-3 py-1">
          {count} of {order.length} completed
        </span>
      </div>
      <div className="h-2 rounded-full bg-[#F4EEF5] overflow-hidden mb-4">
        <div className="h-full bg-[#4A154B] rounded-full transition-[width] duration-500" style={{ width: `${Math.round((count / order.length) * 100)}%` }} />
      </div>
      <div className="space-y-2">
        {order.map((k) => (
          <StatusChip key={k} k={k} done={done[k]} draft={!!drafts[k]} active={k === activeKey} onPick={onPick} />
        ))}
      </div>
      {showSent && <SentToList shares={shares} category={activeKey} />}
      {count > 0 && (
        <button
          type="button"
          data-testid="child-needs-download-report"
          onClick={onDownload}
          className="mt-5 w-full py-3 rounded-md bg-white hover:bg-[#F4EEF5] border border-[#4A154B]/30 text-[#4A154B] text-sm font-bold transition-colors"
        >
          <i className="fa-solid fa-file-pdf mr-1.5"></i>Download my Child's Specific Needs report
        </button>
      )}
      <p className="mt-3 text-[11px] text-slate-500 text-center">{CONTENT.disclaimer}</p>
    </section>
  );
}
