import React from "react";

import { AiGuardFrame } from "../../../components/aiNotice/AiGuard";

const CHIPS = [
  { key: "schedule_change", label: "Schedule Change", icon: "fa-regular fa-clock" },
  { key: "medical_update", label: "Medical Update", icon: "fa-solid fa-notes-medical" },
  { key: "expense_request", label: "Expense Notice", icon: "fa-solid fa-receipt" },
];

export function DraftCard({ value, onChange, onPreset, onTransform, busy, guard }) {
  return (
    <div data-testid="cb-draft-card" className="bg-white rounded-2xl p-6 shadow-md border border-purple-100 mt-6">
      <div className="flex justify-between items-center mb-3 gap-2">
        <h4 className="text-base font-bold text-[#3B1C6B]">Draft Communication Message</h4>
        <span className="text-[0.6875rem] font-semibold text-purple-600 bg-purple-50 px-2.5 py-1 rounded-full whitespace-nowrap">BIFF style</span>
      </div>
      <AiGuardFrame tp="cb" guard={guard} className="mb-3">
        <textarea
          {...guard.inputProps}
          data-testid="cb-draft-input"
          aria-label="Draft communication message"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          maxLength={4000}
          placeholder="Type or paste your message here (e.g., 'You're late for pickup again and you never tell me in advance!')..."
          className="w-full text-xs md:text-sm p-3.5 rounded-xl border border-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-shadow"
        />
      </AiGuardFrame>
      <div className="flex flex-wrap gap-2 mb-4">
        {CHIPS.map((c) => (
          <button
            key={c.key}
            type="button"
            data-testid={`cb-chip-${c.key}`}
            onClick={() => onPreset(c.key)}
            disabled={busy}
            className="text-[0.6875rem] font-medium bg-slate-100 hover:bg-purple-100 text-slate-700 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-60"
          >
            <i className={`${c.icon} text-purple-600 mr-1`}></i> {c.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        data-testid="cb-transform"
        onClick={onTransform}
        disabled={busy || !value.trim()}
        className="w-full py-3 px-4 bg-purple-700 hover:bg-purple-800 disabled:opacity-60 text-white font-bold text-xs rounded-xl shadow transition-colors flex items-center justify-center gap-2"
      >
        <i className={busy ? "fa-solid fa-spinner fa-spin" : "fa-solid fa-wand-magic-sparkles"}></i>
        <span>{busy ? "Getting suggested wording…" : "Get suggested wording"}</span>
      </button>
    </div>
  );
}
