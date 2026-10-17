import React from "react";
import { Loader2, Sparkles } from "lucide-react";

// Shown when a report has no AI summary yet (e.g. made before the AI notice was accepted).
export function AddAiSummaryCard({ tp, busy, onAdd }) {
  return (
    <div className="rounded-3xl border border-dashed border-[#D6CFE8] bg-white p-5 sm:p-6" data-testid={`${tp}-add-ai-summary-card`}>
      <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-2 mb-1">
        <Sparkles size={12} /> AI executive summary
      </div>
      <p className="text-sm text-[#4B4567]">This report has no AI summary. You can ask AI to write one from the report above.</p>
      <button
        type="button"
        onClick={onAdd}
        disabled={busy}
        data-testid={`${tp}-add-ai-summary`}
        className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#3D1A78] px-4 py-2 text-xs font-semibold text-white hover:bg-[#2E1259] disabled:opacity-60"
      >
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
        {busy ? "Writing…" : "Write an AI summary"}
      </button>
    </div>
  );
}
