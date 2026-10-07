import React from "react";

export const RATING_CHIP = {
  Excellent: "bg-emerald-100 text-emerald-900 border-emerald-300",
  Good: "bg-emerald-50 text-emerald-800 border-emerald-200",
  Fair: "bg-amber-50 text-amber-800 border-amber-200",
  "Needs Improvement": "bg-orange-50 text-orange-800 border-orange-200",
};

export function CpIntro({ schema, onStart }) {
  return (
    <div data-testid="cp-assess-intro" className="space-y-4">
      <p className="text-sm text-slate-700 leading-relaxed">
        Rate how often each statement is true for you right now. There are no right or wrong answers. Your
        answers save as you go, so you can stop and come back anytime.
      </p>
      <div className="rounded-xl bg-rose-50 border border-rose-200 px-3 py-2 text-[12px] text-rose-900">
        <i className="fa-solid fa-shield-heart mr-1.5"></i>
        If anything here doesn't feel safe to answer, step away at any time. Your safety and your child's safety
        come first.
      </div>
      <ol className="space-y-1.5">
        {schema.sections.map((s) => (
          <li key={s.id} className="flex items-center gap-2 text-[13px] text-slate-700">
            <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-800 text-[11px] font-bold flex items-center justify-center shrink-0">
              {s.number}
            </span>
            {s.name}
            <span className="ml-auto text-[11px] text-slate-400">{s.questions.length} Qs</span>
          </li>
        ))}
      </ol>
      <button
        type="button"
        data-testid="cp-assess-start"
        onClick={onStart}
        className="w-full py-3 rounded-full bg-[#4c2889] hover:bg-[#371a68] text-white text-sm font-bold shadow-md transition-colors active:scale-[0.98]"
      >
        Begin the assessment <span aria-hidden="true">→</span>
      </button>
    </div>
  );
}

export function CpSection({ section, scale, answers, onAnswer }) {
  const answered = section.questions.filter((q) => answers[q.id] != null).length;
  return (
    <div data-testid={`cp-assess-section-${section.id}`} className="space-y-3">
      <div>
        <h3 className="text-base font-extrabold text-[#4c2889]">
          {section.number}. {section.name}
        </h3>
        <p className="text-[12px] text-slate-500 mt-0.5">{section.goal}</p>
        <p data-testid="cp-assess-section-count" className="text-[11px] font-semibold text-slate-500 mt-1">
          {answered} of {section.questions.length} answered
        </p>
      </div>
      {section.questions.map((q, i) => (
        <div key={q.id} data-testid={`cp-assess-q-${q.id}`} className="rounded-xl border border-purple-100 bg-white p-3">
          <p className="text-[13px] text-slate-800 leading-snug">
            <span className="font-bold text-purple-800 mr-1">{i + 1}.</span>
            {q.prompt}
          </p>
          <div className="grid grid-cols-5 gap-1 mt-2">
            {scale.map((opt) => {
              const on = answers[q.id] === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  data-testid={`cp-assess-${q.id}-${opt.value}`}
                  aria-pressed={on}
                  onClick={() => onAnswer(q.id, opt.value)}
                  className={`py-1.5 rounded-lg border text-[10.5px] font-semibold transition-colors ${
                    on ? "bg-[#4c2889] border-[#4c2889] text-white" : "bg-white border-slate-200 text-slate-600 hover:bg-purple-50"
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export function CpResults({ scores, onDownload, onRetake, onClose }) {
  const focus = new Set(scores.priority_focus || []);
  return (
    <div data-testid="cp-assess-results" className="space-y-4">
      <div className="rounded-2xl bg-[#4c2889] text-white p-4">
        <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-purple-200">Overall</div>
        <div data-testid="cp-assess-overall" className="text-2xl font-extrabold mt-0.5">
          {scores.overall_rating}
        </div>
      </div>
      {focus.size > 0 && (
        <div data-testid="cp-assess-focus" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5">
          <div className="text-[11px] font-bold text-amber-900 uppercase tracking-wide">Priority focus</div>
          <ul className="mt-1 text-[13px] text-amber-900 list-disc pl-4">
            {scores.sections.filter((s) => focus.has(s.id)).map((s) => (
              <li key={s.id}>{s.name}</li>
            ))}
          </ul>
        </div>
      )}
      <ul className="space-y-1.5">
        {scores.sections.map((s) => (
          <li key={s.id} data-testid={`cp-assess-rating-${s.id}`} className="flex items-center gap-2 text-[13px] text-slate-800">
            <span className="flex-1">
              {s.number}. {s.name}
            </span>
            <span className={`shrink-0 px-2 py-0.5 rounded-full border text-[11px] font-bold ${RATING_CHIP[s.rating] || "bg-slate-50 text-slate-600 border-slate-200"}`}>
              {s.rating}
            </span>
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <button type="button" data-testid="cp-assess-download-pdf" onClick={onDownload} className="py-2.5 rounded-full bg-[#4c2889] hover:bg-[#371a68] text-white text-xs font-bold transition-colors">
          <i className="fa-solid fa-file-pdf mr-1.5"></i>Download PDF report
        </button>
        <button type="button" data-testid="cp-assess-retake" onClick={onRetake} className="py-2.5 rounded-full bg-white hover:bg-purple-50 border border-purple-300 text-purple-900 text-xs font-bold transition-colors">
          <i className="fa-solid fa-rotate mr-1.5"></i>Retake the assessment
        </button>
      </div>
      <button type="button" data-testid="cp-assess-close" onClick={onClose} className="w-full py-2 text-xs font-semibold text-slate-500 hover:text-slate-800">
        Close
      </button>
    </div>
  );
}
