import React, { useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import CONTENT from "./foundationBuilderContent.json";

// Card 4 · Foundation Statement. Copy lives in foundationBuilderContent.json
// (mirrored on the backend for the PDF). State comes from useFoundationBuilder.
const PILLAR_STYLE = {
  goals: { icon: "fa-bullseye", bg: "bg-purple-500" },
  child: { icon: "fa-child-reaching", bg: "bg-emerald-500" },
  values: { icon: "fa-list", bg: "bg-orange-500" },
  path: { icon: "fa-handshake", bg: "bg-sky-500" },
};

const STATUS_COPY = {
  pending: "Saving…",
  saving: "Saving…",
  saved: "Saved to your account",
  local: "Saved on this device",
  error: "Saved on this device — couldn't reach your account",
};

const fieldCls =
  "mt-1 w-full px-2.5 py-2 border border-slate-300 rounded-lg text-xs text-slate-900 focus:border-purple-700 focus:ring-2 focus:ring-purple-200 outline-none";

function Pillars() {
  return (
    <div data-testid="foundation-pillars" className="mt-4 space-y-2">
      {CONTENT.pillars.map((p) => (
        <div key={p.key} data-testid={`foundation-pillar-${p.key}`} className="flex items-center gap-3 bg-slate-50 border border-slate-100 rounded-xl p-2.5">
          <div className={`shrink-0 w-10 h-10 rounded-full ${PILLAR_STYLE[p.key].bg} text-white flex items-center justify-center`}>
            <i className={`fa-solid ${PILLAR_STYLE[p.key].icon} text-base`}></i>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold text-slate-900 leading-tight">{p.title}</div>
            <p className="text-[11px] text-slate-600 mt-0.5 leading-snug">{p.body}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function BuilderDialog({ open, onOpenChange, fb, parentName }) {
  const value = (k) => fb.fields[k] ?? (k === "parent_names" ? parentName || "" : "");
  const close = async () => {
    if (await fb.save()) onOpenChange(false);
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="foundation-builder-dialog" className="max-w-md max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-purple-900">{CONTENT.builder_title}</DialogTitle>
          <DialogDescription>Private draft. Your answers save as you type — to your account when you're signed in.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          {CONTENT.fields.map((f) => (
            <label key={f.key} className="block">
              <span className="text-[12px] font-bold text-slate-700">{f.label}</span>
              {f.type === "text" ? (
                <input type="text" data-testid={`foundation-field-${f.key.replace(/_/g, "-")}`} value={value(f.key)} onChange={(e) => fb.update(f.key, e.target.value)} placeholder={f.placeholder} maxLength={3000} className={fieldCls} />
              ) : (
                <textarea data-testid={`foundation-field-${f.key.replace(/_/g, "-")}`} value={value(f.key)} onChange={(e) => fb.update(f.key, e.target.value)} placeholder={f.placeholder} rows={3} maxLength={3000} className={`${fieldCls} resize-y`} />
              )}
            </label>
          ))}
          {STATUS_COPY[fb.status] && (
            <p data-testid="foundation-save-status" data-status={fb.status} className="text-[10px] text-slate-500 text-center">
              {STATUS_COPY[fb.status]}
            </p>
          )}
          <div className="flex items-center gap-2 pt-2 border-t border-slate-200">
            <button type="button" data-testid="foundation-download-pdf" disabled={fb.busy} onClick={fb.download} className="flex-1 py-2.5 rounded-full bg-slate-600 hover:bg-slate-700 disabled:opacity-60 text-white text-xs font-bold transition-colors">
              <i className={`fa-solid ${fb.busy ? "fa-spinner fa-spin" : "fa-file-pdf"} mr-1.5`}></i>
              {fb.busy ? "Building PDF…" : "Download PDF"}
            </button>
            <button type="button" data-testid="foundation-save" onClick={close} className="flex-[1.5] py-2.5 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-xs font-bold transition-colors">
              Save statement
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function FoundationStatementView({ onBack = () => {}, parentName = null, QuickExit = null, fb }) {
  const [builderOpen, setBuilderOpen] = useState(false);
  return (
    <div data-testid="journey-shell" className="space-y-4">
      <section data-testid="door-view-foundation" className="space-y-4">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <button type="button" data-testid="foundation-back" onClick={onBack} className="text-[12px] font-semibold text-purple-700 hover:text-purple-900">
            <i className="fa-solid fa-arrow-left mr-1"></i>
            Back to Self Journey
          </button>
          {QuickExit}
        </div>
        <section data-testid="foundation-brand" className="text-center bg-white border border-slate-200 rounded-2xl py-4 px-4 shadow-sm">
          <div className="text-[22px] font-extrabold text-purple-800 leading-none">SA CoParents</div>
          <div className="text-[9px] font-bold tracking-[0.18em] uppercase text-purple-700 mt-1">Start With Alignment, End With Agreement</div>
        </section>
        <section data-testid="foundation-hero" className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
          <div className="italic text-purple-700 font-bold text-base" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
            {CONTENT.badge}
          </div>
          <h2 className="text-xl font-extrabold text-purple-900 leading-tight mt-1">{CONTENT.title}</h2>
          <p className="text-xs text-slate-600 mt-1.5 leading-snug">{CONTENT.intro}</p>
          <Pillars />
          <button type="button" data-testid="foundation-access" onClick={() => setBuilderOpen(true)} className="mt-4 w-full py-3 rounded-full bg-purple-700 hover:bg-purple-800 text-white text-sm font-bold shadow-md transition-colors flex items-center justify-center gap-2">
            {fb.savedAt ? (
              <span data-testid="foundation-access-saved">
                Saved <i className="fa-solid fa-check mx-1"></i> · Edit
              </span>
            ) : (
              <>
                Access Foundation Statement
                <i className="fa-solid fa-arrow-right text-xs"></i>
              </>
            )}
          </button>
          <div data-testid="foundation-sub-banner" className="mt-4 text-center bg-purple-50 border border-dashed border-purple-200 rounded-xl p-3">
            <div className="italic text-purple-800 font-bold text-base" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
              {CONTENT.footer_title}
            </div>
            <div className="text-[10px] font-extrabold tracking-wider uppercase text-slate-500 mt-1">{CONTENT.footer_tags}</div>
          </div>
        </section>
      </section>
      <BuilderDialog open={builderOpen} onOpenChange={setBuilderOpen} fb={fb} parentName={parentName} />
    </div>
  );
}

export default FoundationStatementView;
