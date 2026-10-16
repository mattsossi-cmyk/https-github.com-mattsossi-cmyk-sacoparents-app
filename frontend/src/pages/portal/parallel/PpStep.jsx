import React from "react";

import { AiNoticeNeeded } from "../../../components/aiNotice/AiGuard";

function OptionCard({ q, o, selected, onPick }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      data-testid={`pp-option-${q.id}-${o.id}`}
      onClick={() => onPick(q.id, o.id)}
      className={`text-left rounded-xl border-2 p-3.5 flex items-start gap-3 transition-[border-color,background-color,box-shadow] ${
        selected ? "border-[#4a2574] bg-[#f4f0fa] shadow-sm" : "border-slate-200 bg-white hover:border-purple-300 hover:bg-purple-50/40"
      }`}
    >
      <span
        className={`mt-0.5 shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
          selected ? "border-[#4a2574] bg-[#4a2574] text-white" : "border-slate-300"
        }`}
      >
        {selected && <i className="fa-solid fa-check text-[9px]"></i>}
      </span>
      <span>
        <span className="block text-sm font-semibold text-slate-900">{o.label}</span>
        <span className="block text-xs text-slate-500 mt-0.5">{o.desc}</span>
      </span>
    </button>
  );
}

function TipCard({ step, tip, busy, error }) {
  return (
    <div data-testid="pp-tip" className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4 flex items-start gap-3">
      <span className="shrink-0 w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center">
        <i className="fa-solid fa-lightbulb"></i>
      </span>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">Tip from your Guide · after {step.title}</p>
        {busy ? (
          <p data-testid="pp-tip-loading" className="text-sm text-emerald-900/70 mt-1">Your Guide is writing a tip…</p>
        ) : tip ? (
          <p data-testid="pp-tip-text" className="text-sm text-emerald-950 leading-relaxed mt-1">{tip}</p>
        ) : (
          <p data-testid="pp-tip-error" className="text-xs text-rose-700 mt-1">{error}</p>
        )}
      </div>
    </div>
  );
}

export function PpStep({ step, index, total, plan, prevStep, tipBusy, tipError, aiNeeded, onPick, onNote, onBack, onNext }) {
  const answered = step.questions.filter((q) => plan.answers[q.id]).length;
  const prevTip = prevStep ? plan.tips[prevStep.key] : "";
  const showTip = prevStep && (tipBusy === prevStep.key || prevTip || (tipError && !tipBusy));
  const last = index === total - 1;
  return (
    <div data-testid={`pp-step-${step.key}`} className="space-y-5">
      {showTip && <TipCard step={prevStep} tip={prevTip} busy={tipBusy === prevStep.key} error={tipError} />}
      {!showTip && prevStep && aiNeeded && <AiNoticeNeeded tp="pp-tip">Your Guide&apos;s step tips appear here after you read and accept the AI privacy notice.</AiNoticeNeeded>}
      <div className="bg-white rounded-3xl border border-purple-100 shadow-lg p-5 sm:p-8">
        <div className="md:hidden mb-4">
          <div className="flex justify-between text-[11px] font-bold text-[#4a2574] uppercase mb-1">
            <span data-testid="pp-mobile-step">Step {index + 1} of {total}</span>
            <span>{Math.round(((index + 1) / total) * 100)}%</span>
          </div>
          <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
            <div className="bg-[#4a2574] h-full" style={{ width: `${((index + 1) / total) * 100}%` }} />
          </div>
        </div>
        <div className="flex items-start gap-4 mb-6">
          <div className="shrink-0 w-12 h-12 rounded-2xl bg-purple-100 text-[#4a2574] flex items-center justify-center text-xl">
            <i className={`fa-solid ${step.icon}`}></i>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#8251b8]">Step {index + 1} of {total}</p>
            <h2 data-testid="pp-step-title" className="text-2xl sm:text-3xl font-extrabold text-[#2d1548]">{step.title}</h2>
            <p className="text-sm text-slate-600 mt-1">{step.intro}</p>
          </div>
        </div>
        <div className="space-y-6">
          {step.questions.map((q) => (
            <fieldset key={q.id} data-testid={`pp-question-${q.id}`}>
              <legend className="text-sm font-bold text-slate-900 mb-2.5">{q.text}</legend>
              <div role="radiogroup" className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {q.options.map((o) => (
                  <OptionCard key={o.id} q={q} o={o} selected={plan.answers[q.id] === o.id} onPick={onPick} />
                ))}
              </div>
            </fieldset>
          ))}
          <div>
            <label htmlFor={`pp-notes-${step.key}`} className="text-sm font-bold text-slate-900">
              Anything to add? <span className="font-normal text-slate-500">(optional)</span>
            </label>
            <textarea
              id={`pp-notes-${step.key}`}
              data-testid={`pp-notes-${step.key}`}
              value={plan.notes[step.key] || ""}
              maxLength={1000}
              rows={3}
              onChange={(e) => onNote(step.key, e.target.value)}
              placeholder="Details that matter for your family, such as times, places or names of professionals."
              className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#8251b8]"
            />
          </div>
        </div>
        <div className="mt-8 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <button
            type="button"
            data-testid="pp-step-back"
            onClick={onBack}
            className="px-5 py-3 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-sm font-semibold transition-colors"
          >
            <i className="fa-solid fa-arrow-left mr-2"></i>Back
          </button>
          <div className="flex items-center gap-3 justify-between sm:justify-end">
            <span data-testid="pp-step-answered" className="text-xs text-slate-500">
              {answered} of {step.questions.length} answered
            </span>
            <button
              type="button"
              data-testid="pp-step-next"
              onClick={onNext}
              className="px-6 py-3 rounded-xl bg-[#388e3c] hover:bg-[#2e7d32] text-white text-sm font-bold shadow-md transition-colors"
            >
              {last ? "Continue to Quick Checks" : "Save & Continue"}
              <i className="fa-solid fa-arrow-right ml-2"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
