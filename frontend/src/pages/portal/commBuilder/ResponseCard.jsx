import React from "react";

const PILLARS = [
  ["BRIEF", "Clear & Short"],
  ["INFORMATIVE", "Objective Facts"],
  ["FRIENDLY", "Neutral Tone"],
  ["FIRM", "Clear Boundaries"],
];
const EXAMPLE =
  "Hi, I noticed the delay for today's pickup. Please let me know your estimated arrival time so we can make sure Sam is ready and keep the routine smooth. Thanks!";

const RiskRow = ({ riskLabel, flagList }) => (
  <div data-testid="cb-risk" className="flex flex-wrap items-center gap-1.5 mb-3 text-[11px]">
    <span
      data-testid="cb-risk-badge"
      className={`px-2 py-0.5 rounded-full font-bold ${
        riskLabel === "Escalation Flag" ? "bg-rose-500/20 text-rose-200" : "bg-emerald-500/20 text-emerald-200"
      }`}
    >
      Tone check: {riskLabel}
    </span>
    {flagList.map((f) => (
      <span key={f} className="px-2 py-0.5 rounded-full bg-white/10 text-purple-200">
        {f}
      </span>
    ))}
  </div>
);

export function ResponseCard({ output, loading, error, riskLabel, flagList, transformed, greyRock, onCopy, onToneSafe, onArchive }) {
  const showReal = !!output && !loading;
  return (
    <div data-testid="cb-response-card" className="bg-gradient-to-br from-purple-900 to-indigo-950 text-white rounded-2xl p-6 shadow-xl border border-purple-800">
      <div className="flex justify-between items-center mb-3 gap-2">
        <span className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-2">
          <i className="fa-solid fa-circle-check text-emerald-400"></i> Refined Peaceful Response
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
        <p data-testid="cb-greyrock-note" className="text-[11px] text-amber-200 mb-2">
          <i className="fa-solid fa-shield-halved mr-1"></i>Grey-rock style: short, factual and neutral.
        </p>
      )}
      {transformed && !loading && riskLabel !== "Neutral" && <RiskRow riskLabel={riskLabel} flagList={flagList} />}
      <div data-testid="cb-output" className="text-sm font-medium leading-relaxed bg-white/5 p-4 rounded-xl border border-white/10 text-purple-100 mb-4 min-h-[88px]">
        {loading ? (
          <span data-testid="cb-output-loading" className="flex items-center gap-2 text-purple-200">
            <i className="fa-solid fa-wand-magic-sparkles animate-pulse"></i> Your coach is rewriting this calmly…
          </span>
        ) : showReal ? (
          <span data-testid="cb-output-text">{output}</span>
        ) : (
          <span data-testid="cb-output-example" className="text-purple-200/80">
            <span className="block text-[10px] uppercase tracking-wider font-bold text-purple-300 mb-1">Example</span>
            “{EXAMPLE}”
          </span>
        )}
      </div>
      {error && !loading && <p data-testid="cb-error" className="text-[11px] text-amber-200 mb-3">{error}</p>}
      <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
        {PILLARS.map(([k, v]) => (
          <div key={k} className="bg-white/10 p-2 rounded-lg">
            <span className="font-bold text-purple-300 block">{k}</span> {v}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 mt-4">
        <button
          type="button"
          data-testid="cb-tone-safe"
          onClick={onToneSafe}
          disabled={!showReal}
          title="Copy with a date/case audit stamp — safe to share with attorneys or mediators"
          className="py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold transition-colors"
        >
          <i className="fa-solid fa-shield-halved mr-1.5"></i>Tone-Safe Copy
        </button>
        <button
          type="button"
          data-testid="cb-archive"
          onClick={onArchive}
          disabled={!showReal}
          className="py-2 rounded-xl bg-white/15 hover:bg-white/25 disabled:opacity-50 text-white text-xs font-bold transition-colors"
        >
          <i className="fa-solid fa-box-archive mr-1.5"></i>Save to History
        </button>
      </div>
    </div>
  );
}
