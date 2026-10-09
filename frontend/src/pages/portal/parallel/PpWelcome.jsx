import React from "react";

const greenBtn =
  "inline-flex items-center justify-center gap-2 px-7 py-4 rounded-2xl bg-[#388e3c] hover:bg-[#2e7d32] text-white font-extrabold text-base shadow-lg hover:shadow-xl transition-[transform,box-shadow,background-color] hover:-translate-y-0.5";

function Feature({ testid, icon, title, short, badge, onOpen }) {
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={onOpen}
      className="text-left p-4 rounded-2xl bg-white border border-purple-100 shadow-sm hover:shadow-md hover:border-purple-200 transition-[box-shadow,border-color]"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="w-10 h-10 rounded-xl bg-purple-100 text-[#4a2574] flex items-center justify-center mb-3">
          <i className={`fa-solid ${icon}`}></i>
        </div>
        {badge && (
          <span data-testid={`${testid}-done`} className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full whitespace-nowrap">
            <i className="fa-solid fa-check mr-1"></i>
            {badge}
          </span>
        )}
      </div>
      <h4 className="font-bold text-gray-900 text-sm">{title}</h4>
      <p className="text-xs text-gray-500 mt-1">{short}</p>
    </button>
  );
}

const heading = "text-[11px] font-bold uppercase tracking-wider text-[#8251b8] mb-3";

export function PpWelcome({ content, plan, onStart, onOpenStep, onOpenCheck, onSummary }) {
  const answered = Object.keys(plan.answers).length;
  const ticks = Object.values(plan.checks || {}).reduce((n, v) => n + v.length, 0);
  const started = answered > 0 || plan.step > 0;
  const resumeStep = Math.min(plan.step, content.steps.length - 1) + 1;
  return (
    <div data-testid="pp-welcome" className="bg-white rounded-3xl shadow-lg border border-purple-100 p-5 sm:p-7 space-y-7">
      <div className="bg-purple-50/80 border border-purple-200/60 rounded-2xl p-4 flex items-center gap-4 shadow-sm">
        <div className="p-3 bg-[#4a2574] text-white rounded-xl shadow-md shrink-0">
          <i className="fa-solid fa-shield-heart text-xl"></i>
        </div>
        <div>
          <h3 data-testid="pp-title" className="font-bold text-[#2d1548] text-base md:text-lg">{content.banner_title}</h3>
          <p className="text-xs md:text-sm text-gray-600 mt-0.5">{content.banner_body}</p>
        </div>
      </div>
      <div>
        <h3 className={heading}>{content.steps.length} planning steps</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {content.steps.map((s, i) => (
            <Feature
              key={s.key}
              testid={`pp-feature-${s.key}`}
              icon={s.icon}
              title={`${s.number}. ${s.title}`}
              short={s.short}
              badge={s.questions.every((q) => plan.answers[q.id]) ? "Done" : null}
              onOpen={() => onOpenStep(i)}
            />
          ))}
        </div>
      </div>
      <div>
        <h3 className={heading}>{content.checklists.length} quick checks</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {content.checklists.map((c, i) => {
            const n = (plan.checks?.[c.key] || []).length;
            return (
              <Feature key={c.key} testid={`pp-feature-check-${c.key}`} icon={c.icon} title={c.title} short={c.short} badge={n ? `${n} ticked` : null} onOpen={() => onOpenCheck(i)} />
            );
          })}
        </div>
      </div>
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <button type="button" data-testid="pp-start" onClick={onStart} className={greenBtn}>
          <i className="fa-solid fa-arrow-right"></i>
          {started ? `Continue My Plan · Step ${resumeStep}` : "Start Building My Plan"}
        </button>
        {(answered > 0 || ticks > 0) && (
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
      <p className="text-[11px] text-gray-500">Private to you · Saved to your account · About 10 minutes</p>
    </div>
  );
}
