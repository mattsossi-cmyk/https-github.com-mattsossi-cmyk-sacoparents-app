import React from "react";

import { PpHistory } from "./PpHistory";
function StepSummary({ step, plan, tipBusy, onEdit }) {
  const note = (plan.notes[step.key] || "").trim();
  const tip = plan.tips[step.key];
  return (
    <div data-testid={`pp-summary-step-${step.key}`} className="rounded-2xl border border-purple-100 overflow-hidden">
      <div className="flex items-center justify-between gap-3 bg-[#f4f0fa] px-4 py-3">
        <h3 className="text-sm font-extrabold text-[#2d1548] flex items-center gap-2">
          <i className={`fa-solid ${step.icon} text-[#4a2574]`}></i>
          {step.number}. {step.title}
        </h3>
        <button type="button" data-testid={`pp-summary-edit-${step.key}`} onClick={onEdit} className="text-xs font-bold text-[#4a2574] hover:underline">
          <i className="fa-solid fa-pen mr-1"></i>Edit
        </button>
      </div>
      <ul className="divide-y divide-purple-50 px-4">
        {step.questions.map((q) => {
          const o = q.options.find((x) => x.id === plan.answers[q.id]);
          return (
            <li key={q.id} className="py-2.5">
              <p className="text-xs text-slate-500">{q.text}</p>
              <p data-testid={`pp-summary-answer-${q.id}`} className={`text-sm font-semibold ${o ? "text-[#2e7d32]" : "text-slate-400 italic font-normal"}`}>
                {o ? o.label : "Not chosen yet"}
              </p>
            </li>
          );
        })}
      </ul>
      {(note || tip || tipBusy === step.key) && (
        <div className="px-4 pb-4 space-y-2">
          {note && <p className="text-xs text-slate-700 bg-slate-50 rounded-lg p-2.5"><span className="font-bold">My notes: </span>{note}</p>}
          {tipBusy === step.key ? (
            <p className="text-xs text-emerald-800/70">Your Guide is writing a tip…</p>
          ) : (
            tip && <p data-testid={`pp-summary-tip-${step.key}`} className="text-xs text-emerald-900 bg-emerald-50 rounded-lg p-2.5"><span className="font-bold">Guide tip: </span>{tip}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function PpSummary({ content, plan, tipBusy, onEdit, onDownload, downloading, historyTick }) {
  const total = content.steps.reduce((n, s) => n + s.questions.length, 0);
  const made = Object.keys(plan.answers).length;
  return (
    <div data-testid="pp-summary" className="bg-white rounded-3xl border border-purple-100 shadow-lg p-5 sm:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-[#8251b8]">Your plan</p>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#2d1548]">Your Parallel Parenting Plan</h2>
          <p className="text-sm text-slate-600 mt-1">{content.banner_title}</p>
          <span data-testid="pp-summary-count" className="inline-block mt-2 text-[10px] font-bold uppercase tracking-wider text-[#4a2574] bg-[#f4f0fa] border border-purple-100 px-2 py-0.5 rounded-full">
            {made} of {total} choices made
          </span>
        </div>
        <button
          type="button"
          data-testid="pp-download-pdf"
          onClick={onDownload}
          disabled={downloading || made === 0}
          className="shrink-0 px-5 py-3 rounded-xl bg-[#388e3c] hover:bg-[#2e7d32] disabled:opacity-60 text-white text-sm font-bold shadow-md transition-colors"
        >
          <i className={`fa-solid ${downloading ? "fa-spinner fa-spin" : "fa-file-pdf"} mr-2`}></i>Download My Plan (PDF)
        </button>
      </div>
      <div className="space-y-4">
        {content.steps.map((s, i) => (
          <StepSummary key={s.key} step={s} plan={plan} tipBusy={tipBusy} onEdit={() => onEdit(i)} />
        ))}
      </div>
      <PpHistory tick={historyTick} />
      <p data-testid="pp-summary-closing" className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-xl p-3">
        <i className="fa-solid fa-circle-info mr-1.5"></i>
        {content.pdf_closing}
      </p>
    </div>
  );
}
