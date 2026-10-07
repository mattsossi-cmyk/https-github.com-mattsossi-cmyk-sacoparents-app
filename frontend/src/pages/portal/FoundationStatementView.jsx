import React, { useEffect, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";

/**
 * FoundationStatementView — iter270.
 *
 * Richer "Foundation Statement" screen reached from Card 4 inside
 * Self Journey. Shows the four-pillar overview from the founder's
 * mockup, then opens a free-text builder dialog with six fields
 * (parent names, children, core hopes, child needs, co-parenting
 * principles, personal commitments). Dialog state persists in
 * localStorage so a parent can leave and come back.
 *
 * Export is intentionally print-based (window.print) — matches the
 * self-assessment pattern and keeps the clinical PDF lockstep rule
 * intact (no new PDF route).
 */

const STORAGE_KEY = "sacoparents_foundation_statement_v1";

const PILLARS = [
  {
    key: "goals",
    title: "Clarify Your Goals",
    body: "Identify your shared hopes for your child's well-being, stability, and future.",
    icon: "fa-bullseye",
    bg: "bg-purple-500",
  },
  {
    key: "child",
    title: "Focus on Your Child",
    body: "Put your child's needs, interests, and daily life at the center of your co-parenting plan.",
    icon: "fa-child-reaching",
    bg: "bg-emerald-500",
  },
  {
    key: "values",
    title: "Set Values and Priorities",
    body: "Outline the core values and principles that will guide your co-parenting decisions.",
    icon: "fa-list",
    bg: "bg-orange-500",
  },
  {
    key: "path",
    title: "Create a Stronger Path Forward",
    body: "Use your Foundation Statement to prepare for productive conversations and agreements.",
    icon: "fa-handshake",
    bg: "bg-sky-500",
  },
];

const BLANK_FORM = {
  parent_names: "",
  child_info: "",
  core_goals: "",
  child_needs: "",
  co_values: "",
  commitments: "",
};

const readStored = () => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
};

const writeStored = (state) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* best-effort */
  }
};

export function FoundationStatementView({
  onBack = () => {},
  parentName = null,
  QuickExit = null,
  SafetyStrip = null,
}) {
  const [builderOpen, setBuilderOpen] = useState(false);
  const [form, setForm] = useState(() => ({
    ...BLANK_FORM,
    ...(readStored() || {}),
    parent_names:
      readStored()?.parent_names || parentName || "",
  }));

  useEffect(() => {
    if (!builderOpen) return;
    const stored = readStored() || {};
    setForm({
      ...BLANK_FORM,
      ...stored,
      parent_names:
        stored.parent_names || parentName || "",
    });
  }, [builderOpen, parentName]);

  useEffect(() => {
    if (!builderOpen) return;
    writeStored(form);
  }, [builderOpen, form]);

  const updateField = (key, value) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div data-testid="journey-shell" className="space-y-4">
      <section
        data-testid="door-view-foundation"
        className="space-y-4"
      >
        {/* Back + Quick-Exit chrome. */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <button
            type="button"
            data-testid="foundation-back"
            onClick={onBack}
            className="text-[12px] font-semibold text-purple-700 hover:text-purple-900"
          >
            <i className="fa-solid fa-arrow-left mr-1"></i>
            Back to Self Journey
          </button>
          {QuickExit}
        </div>

        {SafetyStrip}

        {/* Brand header. */}
        <section
          data-testid="foundation-brand"
          className="text-center bg-white border border-slate-200 rounded-2xl py-4 px-4 shadow-sm"
        >
          <div className="text-[22px] font-extrabold text-purple-800 leading-none">
            SA CoParents
          </div>
          <div className="text-[9px] font-bold tracking-[0.18em] uppercase text-purple-700 mt-1">
            Start With Alignment, End With Agreement
          </div>
        </section>

        {/* Foundation hero. */}
        <section
          data-testid="foundation-hero"
          className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm"
        >
          <div
            className="italic text-purple-700 font-bold text-base"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            A Brighter Future for Your Child
          </div>
          <h2 className="text-xl font-extrabold text-purple-900 leading-tight mt-1">
            Your Foundation Statement
          </h2>
          <p className="text-xs text-slate-600 mt-1.5 leading-snug">
            Your Foundation Statement helps you organize your thoughts,
            identify what matters most, and set the stage for productive
            co-parenting discussions.
          </p>

          {/* Pillars list. */}
          <div
            data-testid="foundation-pillars"
            className="mt-4 space-y-2"
          >
            {PILLARS.map((p) => (
              <div
                key={p.key}
                data-testid={`foundation-pillar-${p.key}`}
                className="flex items-center gap-3 bg-slate-50 border border-slate-100 rounded-xl p-2.5"
              >
                <div
                  className={`shrink-0 w-10 h-10 rounded-full ${p.bg} text-white flex items-center justify-center`}
                >
                  <i className={`fa-solid ${p.icon} text-base`}></i>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-slate-900 leading-tight">
                    {p.title}
                  </div>
                  <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">
                    {p.body}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* CTA. */}
          <button
            type="button"
            data-testid="foundation-access"
            onClick={() => setBuilderOpen(true)}
            className="mt-4 w-full py-3 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-sm font-bold shadow-md transition flex items-center justify-center gap-2"
          >
            Access Foundation Statement
            <i className="fa-solid fa-arrow-right text-xs"></i>
          </button>

          {/* Sub-banner footer. */}
          <div
            data-testid="foundation-sub-banner"
            className="mt-4 text-center bg-purple-50 border border-dashed border-purple-200 rounded-xl p-3"
          >
            <div
              className="italic text-purple-800 font-bold text-base"
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              Same Goals. A Brighter Future.
            </div>
            <div className="text-[10px] font-extrabold tracking-wider uppercase text-slate-500 mt-1">
              Safer Children · Stronger Families · Healthier Tomorrows
            </div>
          </div>
        </section>
      </section>

      {/* Foundation Statement Builder dialog. */}
      <Dialog open={builderOpen} onOpenChange={setBuilderOpen}>
        <DialogContent
          data-testid="foundation-builder-dialog"
          className="max-w-md max-h-[92vh] overflow-y-auto"
        >
          <DialogHeader>
            <DialogTitle className="text-purple-900">
              SA CoParents Foundation Statement
            </DialogTitle>
            <DialogDescription>
              Private draft. Your answers save as you type and stay on
              this device until you choose to share.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <label className="block">
              <span className="text-[12px] font-bold text-slate-700">
                Parent name(s)
              </span>
              <input
                type="text"
                data-testid="foundation-field-parent-names"
                value={form.parent_names}
                onChange={(e) =>
                  updateField("parent_names", e.target.value)
                }
                placeholder="e.g. Sarah & Mark"
                className="mt-1 w-full px-2.5 py-2 border border-slate-300 rounded-lg text-xs text-slate-900 focus:border-purple-700 focus:ring-2 focus:ring-purple-200 outline-none"
              />
            </label>
            <label className="block">
              <span className="text-[12px] font-bold text-slate-700">
                Child(ren) name(s) &amp; age(s)
              </span>
              <input
                type="text"
                data-testid="foundation-field-child-info"
                value={form.child_info}
                onChange={(e) =>
                  updateField("child_info", e.target.value)
                }
                placeholder="e.g. Emma (8), Lucas (5)"
                className="mt-1 w-full px-2.5 py-2 border border-slate-300 rounded-lg text-xs text-slate-900 focus:border-purple-700 focus:ring-2 focus:ring-purple-200 outline-none"
              />
            </label>
            {[
              {
                key: "core_goals",
                label: "1. Core hopes & goals for our child",
                placeholder:
                  "What shared hopes do both parents have for your child's well-being and future?",
              },
              {
                key: "child_needs",
                label: "2. Child needs & priorities",
                placeholder:
                  "What are the essential emotional, educational, and medical priorities right now?",
              },
              {
                key: "co_values",
                label: "3. Agreed co-parenting principles & values",
                placeholder:
                  "What rules or guidelines will govern respectful communication and joint decisions?",
              },
              {
                key: "commitments",
                label: "4. Personal commitments",
                placeholder:
                  "What positive change will you commit to regardless of the other parent's actions?",
              },
            ].map((f) => (
              <label key={f.key} className="block">
                <span className="text-[12px] font-bold text-slate-700">
                  {f.label}
                </span>
                <textarea
                  data-testid={`foundation-field-${f.key.replace(/_/g, "-")}`}
                  value={form[f.key]}
                  onChange={(e) => updateField(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  rows={3}
                  className="mt-1 w-full px-2.5 py-2 border border-slate-300 rounded-lg text-xs text-slate-900 resize-y focus:border-purple-700 focus:ring-2 focus:ring-purple-200 outline-none"
                />
              </label>
            ))}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-200">
              <button
                type="button"
                data-testid="foundation-print"
                onClick={() => {
                  try {
                    window.print();
                  } catch {
                    /* ignore */
                  }
                }}
                className="flex-1 py-2.5 rounded-full bg-slate-600 hover:bg-slate-700 text-white text-xs font-bold transition"
              >
                <i className="fa-solid fa-print mr-1.5"></i>
                Print / PDF
              </button>
              <button
                type="button"
                data-testid="foundation-save"
                onClick={() => setBuilderOpen(false)}
                className="flex-[1.5] py-2.5 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-bold transition"
              >
                Save statement
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default FoundationStatementView;
