import React, { useEffect, useMemo, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";

/**
 * ChildNeedsView — iter269.
 *
 * Richer "Identify Your Child's Specific Needs" screen reached from
 * Card 3 inside Self Journey. Three colour-coded category chips open
 * a checklist dialog each (educational / medical / psychological),
 * plus an "all-needs" overview triggered by the hero CTA. Checkbox
 * state persists per category in localStorage so a parent can leave
 * and return without losing progress.
 *
 * The 1–4 Co-Parenting Roadmap and the Communication Builder card
 * are repeated here per the founder's mockup so the parent has the
 * same next-step affordances they'd see from Self Journey.
 */

const CHECKLIST_STORAGE_PREFIX = "sacoparents_child_needs_checklist_";

const CATEGORIES = {
  educational: {
    label: "Educational Needs",
    icon: "fa-graduation-cap",
    chipBg: "bg-blue-50",
    chipText: "text-blue-700",
    chipBorder: "border-blue-200",
    title: "Educational Needs Checklist",
    items: [
      "Consistent homework and study schedules across both households",
      "Joint access to school portal accounts, report cards, and attendance",
      "Agreed attendance at parent-teacher conferences and school events",
      "Evaluation for learning support, IEP, 504 plans, or tutoring if needed",
    ],
  },
  medical: {
    label: "Medical & Health Needs",
    icon: "fa-briefcase-medical",
    chipBg: "bg-rose-50",
    chipText: "text-rose-700",
    chipBorder: "border-rose-200",
    title: "Medical & Health Needs Checklist",
    items: [
      "Shared access to pediatrician, dentist, and specialist portals",
      "Timely notification of medical appointments, illnesses, or emergencies",
      "Coordinated prescription schedules and medication transfer",
      "Clear agreement on health insurance coverage and out-of-pocket costs",
    ],
  },
  psychological: {
    label: "Psychological & Emotional",
    icon: "fa-heart",
    chipBg: "bg-teal-50",
    chipText: "text-teal-700",
    chipBorder: "border-teal-200",
    title: "Psychological & Emotional Needs Checklist",
    items: [
      "Supportive environment free of adult conflict, criticism, or blame",
      "Access to child therapy or counseling during difficult transitions",
      "Consistent sleep and emotional routines in both homes",
      "Reassurance and permission to love and communicate with both parents",
    ],
  },
  "all-needs": {
    label: "Complete Overview",
    icon: "fa-list-check",
    chipBg: "bg-purple-50",
    chipText: "text-purple-700",
    chipBorder: "border-purple-200",
    title: "Complete Child Needs Overview",
    items: [
      "Educational: unified academic expectations and school monitoring",
      "Medical: shared medical history, doctors, and prescription care",
      "Psychological: emotional safety, counseling support, and low-conflict transitions",
    ],
  },
};

const readChecks = (categoryKey) => {
  try {
    const raw = window.localStorage.getItem(
      CHECKLIST_STORAGE_PREFIX + categoryKey
    );
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const writeChecks = (categoryKey, list) => {
  try {
    window.localStorage.setItem(
      CHECKLIST_STORAGE_PREFIX + categoryKey,
      JSON.stringify(list)
    );
  } catch {
    /* best-effort */
  }
};

export function ChildNeedsView({
  onBack = () => {},
  onOpenAssess = () => {},
  onOpenRelationship = () => {},
  onOpenFoundation = () => {},
  onOpenBiffCoach = () => {},
  QuickExit = null,
  SafetyStrip = null,
  SwitchDoor = null,
}) {
  const [openCategory, setOpenCategory] = useState(null);
  const [checks, setChecks] = useState({});

  // Load the active category's checklist each time the dialog opens.
  useEffect(() => {
    if (!openCategory) return;
    setChecks((prev) => ({
      ...prev,
      [openCategory]: readChecks(openCategory),
    }));
  }, [openCategory]);

  const toggleCheck = (idx) => {
    const list = checks[openCategory] || [];
    const already = list.includes(idx);
    const next = already
      ? list.filter((n) => n !== idx)
      : [...list, idx];
    setChecks((prev) => ({ ...prev, [openCategory]: next }));
    writeChecks(openCategory, next);
  };

  const categoryEntries = useMemo(
    () =>
      Object.entries(CATEGORIES).filter(([key]) => key !== "all-needs"),
    []
  );

  const activeCategory = openCategory ? CATEGORIES[openCategory] : null;
  const activeChecks = openCategory ? checks[openCategory] || [] : [];

  return (
    <div data-testid="journey-shell" className="space-y-4">
      <section
        data-testid="door-view-child-needs"
        className="space-y-4"
      >
        {/* Back + Switch + Quick-Exit chrome. */}
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <button
              type="button"
              data-testid="child-needs-back"
              onClick={onBack}
              className="text-[12px] font-semibold text-purple-700 hover:text-purple-900"
            >
              <i className="fa-solid fa-arrow-left mr-1"></i>
              Back to Self Journey
            </button>
            <div className="flex items-center gap-2">
              {SwitchDoor}
              {QuickExit}
            </div>
          </div>
        </div>

        {SafetyStrip}

        {/* Brand header. */}
        <section
          data-testid="child-needs-brand"
          className="text-center bg-white border border-slate-200 rounded-2xl py-4 px-4 shadow-sm"
        >
          <div className="text-[22px] font-extrabold text-purple-800 leading-none">
            SA CoParents
          </div>
          <div className="text-[9px] font-bold tracking-[0.18em] uppercase text-purple-700 mt-1">
            Start With Alignment, End With Agreement
          </div>
        </section>

        {/* Hero card. */}
        <section
          data-testid="child-needs-hero"
          className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm"
        >
          <div className="italic text-purple-700 font-bold text-base">
            What does my child need?
          </div>
          <h2 className="text-xl font-extrabold text-purple-900 leading-tight mt-1">
            What Does My Child Need?
          </h2>
          <p className="text-xs text-slate-600 mt-1.5 leading-snug">
            Explore your child's developmental, educational, emotional,
            and medical needs to build alignment.
          </p>
          <button
            type="button"
            data-testid="child-needs-explore"
            onClick={() => setOpenCategory("all-needs")}
            className="mt-3 w-full py-3 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-sm font-bold shadow-md transition flex items-center justify-center gap-2"
          >
            Explore Child Needs
            <i className="fa-solid fa-arrow-right text-xs"></i>
          </button>
        </section>

        {/* Category chips. */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 px-1">
            Child Needs Categories
          </div>
          <div
            data-testid="child-needs-categories"
            className="space-y-2"
          >
            {categoryEntries.map(([key, c]) => (
              <button
                key={key}
                type="button"
                data-testid={`child-needs-cat-${key}`}
                onClick={() => setOpenCategory(key)}
                className={`w-full ${c.chipBg} ${c.chipText} border ${c.chipBorder} rounded-xl p-3 flex items-center justify-between shadow-sm transition hover:brightness-95`}
              >
                <div className="flex items-center gap-3">
                  <i className={`fa-solid ${c.icon} text-base`}></i>
                  <span className="font-bold text-sm">{c.label}</span>
                </div>
                <i className="fa-solid fa-chevron-right text-xs opacity-70"></i>
              </button>
            ))}
          </div>
        </div>

        {/* 1–4 roadmap repeated per mockup. */}
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 px-1">
            Co-Parenting Roadmap
          </div>
          <div
            data-testid="child-needs-roadmap"
            className="space-y-2"
          >
            {[
              {
                num: 1,
                color: "bg-violet-500",
                title: "Assess Your Situation",
                body: "Understand where you are today, your strengths, and challenges.",
                onClick: onOpenAssess,
                testid: "child-needs-roadmap-assess",
              },
              {
                num: 2,
                color: "bg-indigo-500",
                title: "Understand Your Relationship",
                body: "Explore communication patterns and co-parenting styles.",
                onClick: onOpenRelationship,
                testid: "child-needs-roadmap-relationship",
              },
              {
                num: 3,
                color: "bg-emerald-500",
                title: "Identify Specific Needs",
                body: "Focus on education, health, and developmental stability.",
                onClick: () => setOpenCategory("all-needs"),
                testid: "child-needs-roadmap-needs",
              },
              {
                num: 4,
                color: "bg-orange-500",
                title: "Create Foundation Statement",
                body: "Build the foundation for productive discussions and agreements.",
                onClick: onOpenFoundation,
                testid: "child-needs-roadmap-foundation",
              },
            ].map((r) => (
              <button
                key={r.num}
                type="button"
                data-testid={r.testid}
                onClick={r.onClick}
                className="w-full bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-purple-200 rounded-xl p-3 flex items-center gap-3 text-left transition"
              >
                <div
                  className={`shrink-0 w-8 h-8 rounded-full ${r.color} text-white font-extrabold flex items-center justify-center`}
                >
                  {r.num}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-slate-900 leading-tight">
                    {r.title}
                  </div>
                  <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">
                    {r.body}
                  </p>
                </div>
                <i className="fa-solid fa-chevron-right text-slate-400 text-xs"></i>
              </button>
            ))}
          </div>
        </div>

        {/* Communication Builder repeated per mockup. */}
        <button
          type="button"
          data-testid="child-needs-biff"
          onClick={onOpenBiffCoach}
          className="w-full bg-gradient-to-br from-purple-100 to-purple-200 border-2 border-purple-300 hover:border-purple-700 rounded-2xl p-4 shadow-md hover:shadow-lg transition flex items-center gap-3 text-left"
        >
          <div className="shrink-0 w-12 h-12 rounded-full bg-purple-700 text-white flex items-center justify-center">
            <i className="fa-solid fa-comments text-lg"></i>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-extrabold text-purple-900 leading-tight">
              Communication Builder
            </div>
            <p className="text-[11px] text-slate-700 mt-0.5 leading-snug">
              Refine messages, reduce conflict, and keep focus on your
              child.
            </p>
          </div>
          <i className="fa-solid fa-chevron-right text-purple-700 text-sm"></i>
        </button>
      </section>

      {/* Checklist dialog — one component drives all four categories. */}
      <Dialog
        open={!!openCategory}
        onOpenChange={(open) => {
          if (!open) setOpenCategory(null);
        }}
      >
        <DialogContent
          data-testid="child-needs-checklist-dialog"
          className="max-w-md max-h-[90vh] overflow-y-auto"
        >
          {activeCategory && (
            <>
              <DialogHeader>
                <DialogTitle
                  data-testid="child-needs-checklist-title"
                  className="text-purple-900"
                >
                  {activeCategory.title}
                </DialogTitle>
                <DialogDescription>
                  Tick what feels agreed and in place today. Nothing
                  here is shared — this is your private checklist.
                </DialogDescription>
              </DialogHeader>
              <div
                data-testid="child-needs-checklist-items"
                className="divide-y divide-slate-100"
              >
                {activeCategory.items.map((item, idx) => (
                  <label
                    key={idx}
                    className="flex items-start gap-3 py-2.5 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      data-testid={`child-needs-check-${openCategory}-${idx}`}
                      checked={activeChecks.includes(idx)}
                      onChange={() => toggleCheck(idx)}
                      className="mt-1 w-4 h-4 accent-purple-700 shrink-0"
                    />
                    <span className="text-[13px] text-slate-800 leading-snug">
                      {item}
                    </span>
                  </label>
                ))}
              </div>
              <button
                type="button"
                data-testid="child-needs-checklist-save"
                onClick={() => setOpenCategory(null)}
                className="mt-3 w-full py-3 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-sm font-bold transition"
              >
                Save &amp; Return
              </button>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default ChildNeedsView;
