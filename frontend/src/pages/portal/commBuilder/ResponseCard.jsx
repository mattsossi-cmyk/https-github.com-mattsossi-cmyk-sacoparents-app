import React from "react";

import { SuggestUnavailable } from "./SuggestUnavailable";

const PILLARS = [
  ["BRIEF", "Clear & Short"],
  ["INFORMATIVE", "Objective Facts"],
  ["FRIENDLY", "Neutral Tone"],
  ["FIRM", "Clear Boundaries"],
];
const EXAMPLE =
  "Hi, I noticed the delay for today's pickup. Please let me know your estimated arrival time so we can make sure Sam is ready and keep the routine smooth. Thanks!";

// Tone check is only shown after AI actually reviewed the draft.
const RiskRow = ({ riskLabel, flagList }) => (
  <div data-testid="cb-risk" className="flex flex-wrap items-center gap-1.5 mb-3 text-[0.6875rem]">
    <span
      data-testid="cb-risk-badge"
      className={`px-2 py-0.5 rounded-full font-bold ${
        riskLabel === "Escalation Flag" ? "bg-rose-500/20 text-rose-200" : "bg-emerald-500/20 text-emerald-200"
      }`}
    >
      AI tone check: {riskLabel}
    </span>
    {flagList.map((f) => (
      <span key={f} className="px-2 py-0.5 rounded-full bg-white/10 text-purple-200">
        {f}
      </span>
    ))}
  </div>
);

function Output({ status, output, raw, greyRock, onRetry, onUseTemplate }) {
  if (status === "loading")
    return (
      <span data-testid="cb-output-loading" className="flex items-center gap-2 text-purple-200">
        <i className="fa-solid fa-wand-magic-sparkles animate-pulse"></i> Getting suggested wording…
      </span>
    );
  if (status === "ai") return <span data-testid="cb-output-text" className="whitespace-pre-wrap">{output}</span>;
  if (status === "unavailable")
    return <SuggestUnavailable tp="cb" raw={raw} greyRock={greyRock} onRetry={onRetry} onUseTemplate={onUseTemplate} />;
  return (
    <span data-testid="cb-output-example" className="text-purple-200/80">
      <span className="block text-[0.625rem] uppercase tracking-wider font-bold text-purple-300 mb-1">Example</span>
      &ldquo;{EXAMPLE}&rdquo;
    </span>
  );
}

export function ResponseCard({ output, status, raw, riskLabel, flagList, greyRock, onCopy, onToneSafe, onArchive, onRetry, onUseTemplate }) {
  const showReal = status === "ai" && !!output;
  const act = "py-2 rounded-xl disabled:opacity-50 text-white text-xs font-bold transition-colors";
  return (
    <div data-testid="cb-response-card" data-status={status} className="bg-gradient-to-br from-purple-900 to-indigo-950 text-white rounded-2xl p-4 sm:p-6 shadow-xl border border-purple-800">
      <div className="flex flex-wrap justify-between items-center mb-3 gap-2">
        <span data-testid="cb-response-title" className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-2">
          <i className="fa-solid fa-pen-nib text-emerald-400"></i> Suggested wording
        </span>
        <button
          type="button"
          data-testid="cb-copy"
          onClick={onCopy}
          disabled={!showReal}
          className="text-xs bg-white/10 hover:bg-white/20 disabled:opacity-50 text-purple-200 px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 shrink-0"
        >
          <i className="fa-regular fa-copy"></i> Copy Text
        </button>
      </div>
      {greyRock && (
        <p data-testid="cb-greyrock-note" className="text-[0.6875rem] text-amber-200 mb-2">
          <i className="fa-solid fa-sliders mr-1" aria-hidden="true"></i>Grey-rock style: short, factual and neutral.
        </p>
      )}
      {showReal && <RiskRow riskLabel={riskLabel} flagList={flagList} />}
      <div data-testid="cb-output" className="text-sm font-medium leading-relaxed bg-white/5 p-4 rounded-xl border border-white/10 text-purple-100 mb-2 min-h-[88px]">
        <Output status={status} output={output} raw={raw} greyRock={greyRock} onRetry={onRetry} onUseTemplate={onUseTemplate} />
      </div>
      {showReal && (
        <p data-testid="cb-output-note" className="text-[0.6875rem] text-purple-200/90 mb-3">
          AI-suggested and checked against your dates, times and questions. Read it and edit it before you send.
        </p>
      )}
      <div className="grid grid-cols-4 gap-2 text-center text-[0.625rem] mt-2">
        {PILLARS.map(([k, v]) => (
          <div key={k} className="bg-white/10 p-2 rounded-lg">
            <span className="font-bold text-purple-300 block">{k}</span> {v}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 mt-4">
        <button type="button" data-testid="cb-tone-safe" onClick={onToneSafe} disabled={!showReal} title="Copy with a date stamp for your own records" className={`${act} bg-emerald-600 hover:bg-emerald-700`}>
          <i className="fa-regular fa-calendar-check mr-1.5"></i>Copy with date stamp
        </button>
        <button type="button" data-testid="cb-archive" onClick={onArchive} disabled={!showReal} className={`${act} bg-white/15 hover:bg-white/25`}>
          <i className="fa-solid fa-box-archive mr-1.5"></i>Save to History
        </button>
      </div>
    </div>
  );
}
