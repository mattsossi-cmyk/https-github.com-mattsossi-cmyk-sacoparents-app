/**
 * cost/CostSplitterEntriesList.jsx — extracted from
 * `CostSplitterPanel.jsx` (2026-03-06).
 *
 * Renders the expandable "Show my N entries" list underneath the
 * log-expense form. Delete-per-row support: fires the passed
 * `onRemove(cost_id)` callback; the parent panel owns the confirm
 * dialog + API call + refresh.
 */
import React, { useState } from "react";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";

function formatMoney(cents, currency = "USD") {
  const n = (cents || 0) / 100;
  if (currency === "USD") {
    return n.toLocaleString(undefined, {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return `${n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${currency}`;
}

export default function CostSplitterEntriesList({ rows, categories, onRemove }) {
  const [expanded, setExpanded] = useState(false);
  if (!rows || rows.length === 0) return null;

  const catLookup = (key) => categories.find((c) => c.key === key)?.label || key;

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="text-sm text-[#1E7A55] hover:text-[#0F5638] inline-flex items-center gap-1"
        data-testid="cost-splitter-toggle"
      >
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {expanded ? "Hide" : "Show"} my {rows.length} entr{rows.length === 1 ? "y" : "ies"}
      </button>
      {expanded && (
        <div className="mt-3 space-y-2" data-testid="cost-splitter-rows">
          {rows.map((r) => (
            <div
              key={r.cost_id}
              className="rounded-xl border border-[#DEF3E7] bg-white px-3 py-2 flex flex-wrap items-center gap-3"
            >
              <div className="flex-1 min-w-[160px]">
                <div className="text-sm font-semibold text-[#1A1330]">
                  {r.activity_label}
                </div>
                <div className="text-[0.6875rem] text-[#4B4567]">
                  {catLookup(r.category)}
                  {r.incurred_on ? ` · ${r.incurred_on}` : ""}
                  {r.note ? ` · ${r.note}` : ""}
                </div>
              </div>
              <div className="font-serif text-base text-[#1A1330]">
                {formatMoney(r.amount_cents, r.currency)}
              </div>
              <button
                type="button"
                onClick={() => onRemove(r.cost_id)}
                aria-label="Remove entry"
                data-testid={`cost-splitter-remove-${r.cost_id}`}
                className="text-[#9A3A23] hover:bg-[#FDECEC] rounded-full p-1.5"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
