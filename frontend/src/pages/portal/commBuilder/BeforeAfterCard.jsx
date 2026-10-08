import React from "react";

const EXAMPLE = {
  original: "You're late again and you never tell me!",
  biff: "Hi, please let me know your ETA for pickup today so I can ensure Sam is ready. Thanks!",
  grey: "Please confirm your ETA for pickup today.",
};

const tab = (active) =>
  `px-3 py-1 rounded-full transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${active ? "bg-purple-700 text-white shadow" : "text-purple-800 hover:bg-purple-100"}`;

// Split view: the original message next to its BIFF rewrite (example first, then the parent's own).
export function BeforeAfterCard({ mode, onMode, canShowYours, original, transformed, loading, riskLabel, greyRock }) {
  const yours = mode === "yours" && canShowYours;
  const before = yours ? original : EXAMPLE.original;
  const after = yours ? transformed : greyRock ? EXAMPLE.grey : EXAMPLE.biff;
  const friction = !yours || riskLabel === "Escalation Flag" ? "High Friction" : "Low Friction";
  return (
    <div data-testid="cb-before-after" data-mode={yours ? "yours" : "example"} className="bg-white rounded-2xl p-5 shadow-md border border-purple-100">
      <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
        <div>
          <h3 className="text-sm font-extrabold text-[#3B1C6B] uppercase tracking-wider">
            <i className="fa-solid fa-right-left text-purple-600 mr-2"></i>Before &amp; After
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">See how Emergent AI calms a message before you send it.</p>
        </div>
        <div role="tablist" className="inline-flex bg-purple-50 border border-purple-100 rounded-full p-0.5 text-[11px] font-bold">
          <button type="button" role="tab" aria-selected={!yours} data-testid="cb-ba-example" onClick={() => onMode("example")} className={tab(!yours)}>
            Example
          </button>
          <button type="button" role="tab" aria-selected={yours} data-testid="cb-ba-yours" disabled={!canShowYours} onClick={() => onMode("yours")} className={tab(yours)}>
            Your message
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div data-testid="cb-ba-before" className="rounded-xl border border-rose-200 bg-rose-50/70 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-rose-700 mb-2">
            <i className="fa-solid fa-fire-flame-curved mr-1"></i>Original Text ({friction})
          </p>
          <p data-testid="cb-ba-before-text" className="text-sm text-rose-950 leading-relaxed whitespace-pre-wrap break-words">{before}</p>
        </div>
        <div data-testid="cb-ba-after" className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 mb-2">
            <i className="fa-solid fa-wand-magic-sparkles mr-1"></i>AI Transformed (BIFF)
          </p>
          {yours && loading ? (
            <p data-testid="cb-ba-after-loading" className="text-xs text-slate-500">Rewriting your message…</p>
          ) : (
            <p data-testid="cb-ba-after-text" className="text-sm text-emerald-950 leading-relaxed whitespace-pre-wrap break-words">{after}</p>
          )}
        </div>
      </div>
    </div>
  );
}
