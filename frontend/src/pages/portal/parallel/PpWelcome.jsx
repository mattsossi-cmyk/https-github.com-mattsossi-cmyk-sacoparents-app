import React from "react";

const greenBtn =
  "inline-flex items-center justify-center gap-2 px-7 py-4 rounded-2xl bg-[#388e3c] hover:bg-[#2e7d32] text-white font-extrabold text-base sm:text-lg shadow-lg hover:shadow-xl transition-[transform,box-shadow,background-color] hover:-translate-y-0.5";

function Feature({ step, done, onOpen }) {
  return (
    <button
      type="button"
      data-testid={`pp-feature-${step.key}`}
      onClick={onOpen}
      className="text-left p-4 rounded-2xl bg-white border border-purple-100 shadow-sm hover:shadow-md hover:border-purple-200 transition-[box-shadow,border-color]"
    >
      <div className="flex items-start justify-between">
        <div className="w-10 h-10 rounded-xl bg-purple-100 text-[#4a2574] flex items-center justify-center mb-3">
          <i className={`fa-solid ${step.icon}`}></i>
        </div>
        {done && (
          <span data-testid={`pp-feature-done-${step.key}`} className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
            <i className="fa-solid fa-check mr-1"></i>Done
          </span>
        )}
      </div>
      <h4 className="font-bold text-gray-900 text-sm">{step.title}</h4>
      <p className="text-xs text-gray-500 mt-1">{step.short}</p>
    </button>
  );
}

export function PpWelcome({ content, plan, onStart, onOpenStep, onSummary }) {
  const answered = Object.keys(plan.answers).length;
  const started = answered > 0 || plan.step > 0;
  const resumeStep = Math.min(plan.step, content.steps.length - 1) + 1;
  return (
    <div data-testid="pp-welcome" className="bg-white rounded-3xl shadow-xl overflow-hidden border border-purple-100">
      <div className="bg-gradient-to-b from-purple-50 via-white to-white p-6 md:p-10 text-center">
        <div className="flex flex-col items-center mb-6">
          <div className="w-16 h-16 rounded-full bg-[#4a2574] text-white flex items-center justify-center shadow-lg mb-2">
            <i className="fa-solid fa-handshake-angle text-3xl"></i>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-[#2d1548] tracking-tight">
            SA CoParents<span className="text-sm font-semibold align-top text-[#4a2574]">™</span>
          </h1>
          <p className="text-xs md:text-sm font-bold uppercase tracking-widest text-[#4a2574] mt-1">Start with Alignment • End with Agreement</p>
        </div>
        <div className="max-w-3xl mx-auto my-6 rounded-2xl overflow-hidden shadow-lg border border-purple-100 bg-gradient-to-r from-purple-900 to-indigo-900 text-white p-8 relative">
          <div className="relative z-10 flex flex-col items-center">
            <span className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-md px-4 py-1.5 rounded-full text-xs font-semibold mb-4 text-purple-100">
              <i className="fa-solid fa-shield-halved"></i> {content.badge}
            </span>
            <h2 data-testid="pp-title" className="text-3xl md:text-5xl font-black mb-2">
              Parallel Parenting
              <br />
              Option Builder
            </h2>
            <p className="text-base md:text-xl text-purple-100 font-medium max-w-xl mt-2">{content.tagline}</p>
          </div>
          <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-purple-500/20 rounded-full blur-2xl" />
          <div className="absolute -top-10 -right-10 w-40 h-40 bg-indigo-500/20 rounded-full blur-2xl" />
        </div>
        <div className="max-w-2xl mx-auto bg-purple-50/80 border border-purple-200/60 rounded-2xl p-4 my-6 flex items-center gap-4 text-left shadow-sm">
          <div className="p-3 bg-[#4a2574] text-white rounded-xl shadow-md shrink-0">
            <i className="fa-solid fa-shield-heart text-xl"></i>
          </div>
          <div>
            <h3 className="font-bold text-[#2d1548] text-base md:text-lg">{content.banner_title}</h3>
            <p className="text-xs md:text-sm text-gray-600 mt-0.5">{content.banner_body}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 max-w-4xl mx-auto my-8">
          {content.steps.map((s, i) => (
            <Feature key={s.key} step={s} done={s.questions.every((q) => plan.answers[q.id])} onOpen={() => onOpenStep(i)} />
          ))}
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button type="button" data-testid="pp-start" onClick={onStart} className={greenBtn}>
            <i className="fa-solid fa-arrow-right"></i>
            {started ? `Continue My Plan · Step ${resumeStep}` : "Start Building My Plan"}
          </button>
          {answered > 0 && (
            <button
              type="button"
              data-testid="pp-view-plan"
              onClick={onSummary}
              className="px-6 py-4 rounded-2xl bg-white border-2 border-purple-200 hover:border-[#4a2574] text-[#4a2574] font-bold transition-colors"
            >
              View My Plan
            </button>
          )}
        </div>
        <p className="text-[11px] text-gray-500 mt-4">Private to you · Saved to your account · About 10 minutes</p>
      </div>
    </div>
  );
}
