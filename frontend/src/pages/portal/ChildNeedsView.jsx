import React, { useState } from "react";
import { toast } from "sonner";

import CONTENT from "./childNeedsContent.json";
import { ChildNeedsForm } from "./childNeeds/ChildNeedsForm";
import { useGuideChat } from "./guide/useGuideChat";
import { JourneyPage } from "./selfJourney/JourneyPage";
import { NEEDS_ART } from "./selfJourney/selfJourneyArt";

const ORDER = NEEDS_ART.items.map((i) => i.key);
const CATS = Object.fromEntries(CONTENT.categories.map((c) => [c.key, c]));
const TAB_ON = {
  educational: "border-green-400 bg-green-50 text-green-800",
  medical: "border-sky-400 bg-sky-50 text-sky-800",
  psychological: "border-purple-400 bg-purple-50 text-purple-800",
};
const GREETING = "Hi, I'm your Child Needs Guide. Ask me how to describe your child's school, health or emotional needs so both homes can support them.";
const SUGGESTIONS = ["What should I include here?", "How do I keep this child-focused?", "How can both homes stay consistent?"];

function NeedsTabs({ activeKey, done, onPick }) {
  return (
    <div role="tablist" className="grid grid-cols-3 gap-2">
      {NEEDS_ART.items.map((it) => {
        const on = it.key === activeKey;
        return (
          <button
            key={it.key}
            type="button"
            role="tab"
            aria-selected={on}
            data-testid={`child-needs-tab-${it.key}`}
            onClick={() => onPick(it.key)}
            className={`rounded-2xl border-2 px-2 py-3 flex flex-col items-center gap-1 text-center transition-[border-color,background-color,box-shadow] ${
              on ? `${TAB_ON[it.key]} shadow-md` : "border-slate-200 bg-white text-slate-600 hover:border-purple-200"
            }`}
          >
            <i className={`fa-solid ${it.icon} text-lg`}></i>
            <span className="text-[12px] font-extrabold leading-tight">{it.label}</span>
            {done[it.key] ? (
              <span data-testid={`child-needs-${it.key}-completed`} className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5 whitespace-nowrap">
                Completed <i className="fa-solid fa-check text-[9px]"></i>
              </span>
            ) : (
              <span className="text-[10px] font-semibold text-slate-400">Not started</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// Your Child's Specific Needs: picture bubbles + tabs switch the form on the left. `needs` is owned by JourneyShell.
export function ChildNeedsView({ onBack, onQuickExit, needs, parentName, initialOpenKey = null, safetyFlag }) {
  const { state, saveCategory, downloadReport } = needs;
  const done = Object.fromEntries(ORDER.map((k) => [k, !!state.completed_at?.[k]]));
  const [activeKey, setActiveKey] = useState(initialOpenKey || ORDER.find((k) => !done[k]) || ORDER[0]);
  const category = CATS[activeKey];
  const chat = useGuideChat("/journey-guide/child-needs/chat", { section: category.form_title, safety_flagged: !!safetyFlag });
  const doneCount = ORDER.filter((k) => done[k]).length;

  const pick = (k) => {
    setActiveKey(k);
    document.getElementById("cn-work")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const submit = async (values) => {
    try {
      const next = await saveCategory(activeKey, values);
      const ok = await downloadReport(next.answers, parentName);
      if (ok) toast.success("Saved. Your Child's Specific Needs report is downloading.");
      const upNext = ORDER.find((k) => !next.completed_at?.[k]);
      if (upNext) pick(upNext);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't save right now. Please try again.");
    }
  };

  return (
    <JourneyPage
      tp="cn"
      hero={{ title: CONTENT.title, subtitle: CONTENT.subtitle, pill: `${doneCount} of ${ORDER.length} completed`, pct: Math.round((doneCount / ORDER.length) * 100) }}
      art={NEEDS_ART}
      onArt={pick}
      artState={{ done, activeKey }}
      chat={chat}
      chatProps={{ title: "Child Needs Guide", greeting: GREETING, suggestions: SUGGESTIONS }}
      onBack={onBack}
      onQuickExit={onQuickExit}
      footer="Your Child's Specific Needs"
    >
      <div data-testid="door-view-child-needs" className="space-y-5">
        <NeedsTabs activeKey={activeKey} done={done} onPick={pick} />
        <section id="cn-work" data-testid={`child-needs-panel-${activeKey}`} className="bg-white rounded-3xl border border-purple-100 shadow-lg p-5 sm:p-7 scroll-mt-6">
          <h3 data-testid="child-needs-form-title" className="text-xl sm:text-2xl font-extrabold text-[#3B1C6B]">
            {category.form_title}
          </h3>
          <p className="text-sm text-slate-600 mt-1 mb-5">{category.card_desc}</p>
          <ChildNeedsForm key={activeKey} category={category} initial={state.answers?.[activeKey]} onSubmit={submit} />
        </section>
        {doneCount > 0 && (
          <button
            type="button"
            data-testid="child-needs-download-report"
            onClick={() => downloadReport(state.answers, parentName)}
            className="w-full py-3 rounded-full bg-white hover:bg-purple-50 border border-purple-300 text-purple-900 text-sm font-bold transition-colors"
          >
            <i className="fa-solid fa-file-pdf mr-1.5"></i>Download my Child's Specific Needs report
          </button>
        )}
        <p className="text-[11px] text-slate-500 text-center">{CONTENT.disclaimer}</p>
      </div>
    </JourneyPage>
  );
}

export default ChildNeedsView;
