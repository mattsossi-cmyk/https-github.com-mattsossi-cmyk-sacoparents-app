import React, { useState } from "react";
import { toast } from "sonner";

import CONTENT from "./childNeedsContent.json";
import { ChildNeedsForm } from "./childNeeds/ChildNeedsForm";
import { useChildNeeds } from "./childNeeds/useChildNeeds";

// Card 3 · "Your Child's Specific Needs" — founder mockup (3 assessment cards).
const THEMES = {
  medical: { card: "from-white to-sky-100 border-sky-200", icon: "fa-stethoscope text-sky-600", title: "text-sky-700", btn: "bg-sky-600 hover:bg-sky-700" },
  educational: { card: "from-white to-green-100 border-green-200", icon: "fa-book-open text-green-600", title: "text-green-700", btn: "bg-green-600 hover:bg-green-700" },
  psychological: { card: "from-white to-orange-100 border-orange-200", icon: "fa-brain text-orange-600", title: "text-orange-700", btn: "bg-orange-600 hover:bg-orange-700" },
};

function NeedsCard({ category, completed, onOpen }) {
  const t = THEMES[category.key];
  return (
    <div data-testid={`child-needs-card-${category.key}`} className={`rounded-[22px] border-2 bg-gradient-to-br ${t.card} p-5 shadow-[0_6px_20px_rgba(0,0,0,0.06)] space-y-4`}>
      <div className="flex items-start gap-3.5">
        <div className="shrink-0 w-14 h-14 rounded-full bg-white shadow flex items-center justify-center">
          <i className={`fa-solid ${t.icon} text-2xl`}></i>
        </div>
        <div className="min-w-0">
          <h2 className={`text-xl font-extrabold leading-tight ${t.title}`}>{category.card_title}</h2>
          <p className="text-[13.5px] text-slate-600 leading-snug mt-1">{category.card_desc}</p>
        </div>
      </div>
      <button
        type="button"
        data-testid={`child-needs-open-${category.key}`}
        onClick={onOpen}
        className={`w-full py-3.5 px-4 rounded-full text-white text-[14px] font-extrabold shadow-md flex items-center justify-center gap-2 transition-[filter,transform] active:scale-[0.98] ${t.btn}`}
      >
        {completed ? (
          <span data-testid={`child-needs-${category.key}-completed`}>
            Completed <i className="fa-solid fa-check mx-1"></i> · Edit
          </span>
        ) : (
          <>
            <span>{category.button}</span>
            <span aria-hidden="true">→</span>
          </>
        )}
      </button>
    </div>
  );
}

export function ChildNeedsView({ onBack = () => {}, QuickExit = null, userId, parentName, initialOpenKey = null }) {
  const { state, saveCategory, downloadReport } = useChildNeeds(userId);
  const [openKey, setOpenKey] = useState(initialOpenKey);
  const category = CONTENT.categories.find((c) => c.key === openKey);
  const anyDone = CONTENT.categories.some((c) => state.completed_at?.[c.key]);

  const submit = async (values) => {
    try {
      const next = await saveCategory(openKey, values);
      setOpenKey(null);
      const ok = await downloadReport(next.answers, parentName);
      if (ok) toast.success("Saved. Your Child's Specific Needs report is downloading.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't save right now. Please try again.");
    }
  };

  return (
    <div data-testid="door-view-child-needs" className="space-y-5 max-w-[540px] mx-auto">
      <div className="flex items-center justify-between gap-2">
        <button type="button" data-testid="child-needs-back" onClick={onBack} className="text-sm font-semibold text-purple-800 hover:underline">
          <i className="fa-solid fa-arrow-left mr-1.5"></i>Back
        </button>
        {QuickExit}
      </div>

      <header className="text-center pt-1">
        <div className="text-[1.8rem] font-extrabold text-[#4c2889] tracking-tight">SA CoParents</div>
        <div className="text-[11px] font-bold tracking-[0.18em] text-[#4c2889] uppercase mt-0.5">{CONTENT.brand_tagline}</div>
      </header>
      <div className="text-center">
        <h1 data-testid="child-needs-title" className="text-4xl font-extrabold text-[#4c2889] leading-[1.15] tracking-tight">
          {CONTENT.title}
        </h1>
        <p className="text-[15px] text-slate-600 leading-snug mt-2 px-2">{CONTENT.subtitle}</p>
      </div>

      <div className="space-y-5">
        {CONTENT.categories.map((c) => (
          <NeedsCard key={c.key} category={c} completed={!!state.completed_at?.[c.key]} onOpen={() => setOpenKey(c.key)} />
        ))}
      </div>

      {anyDone && (
        <button
          type="button"
          data-testid="child-needs-download-report"
          onClick={() => downloadReport(state.answers, parentName)}
          className="w-full py-3 rounded-full bg-white hover:bg-purple-50 border border-purple-300 text-purple-900 text-sm font-bold transition-colors"
        >
          <i className="fa-solid fa-file-pdf mr-1.5"></i>Download my Child's Specific Needs report
        </button>
      )}

      <div className="text-center px-4 py-4 bg-purple-50 rounded-2xl border border-dashed border-purple-300 text-[#4c2889] text-[13px] font-extrabold tracking-wide uppercase">
        {CONTENT.footer}
      </div>

      <ChildNeedsForm
        category={category}
        initial={state.answers?.[openKey]}
        open={!!openKey}
        onOpenChange={(o) => !o && setOpenKey(null)}
        onSubmit={submit}
      />
    </div>
  );
}

export default ChildNeedsView;
