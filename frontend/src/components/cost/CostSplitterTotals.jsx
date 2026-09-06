/**
 * cost/CostSplitterTotals.jsx — extracted from `CostSplitterPanel.jsx`
 * (2026-03-06) to keep the panel under component-size budget.
 *
 * Renders the three-box totals card (You / Co-parent / Combined).
 * Pure presentation — accepts already-computed cent totals and a
 * boolean `hasCompare` flag from the parent panel.
 */
import React from "react";

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

export default function CostSplitterTotals({
  selfTotal,
  coparentTotal,
  combinedTotal,
  selfCount,
  coparentCount,
  hasCompare,
  coparentName,
}) {
  const entryLabel = (n) => `${n} entr${n === 1 ? "y" : "ies"}`;
  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4"
      data-testid="cost-splitter-totals"
    >
      <div className="rounded-2xl border border-[#C7E5D3] bg-[#F1F9F4] p-4">
        <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] mb-1">
          You
        </div>
        <div
          className="font-serif text-2xl text-[#1A1330]"
          data-testid="cost-splitter-self-total"
        >
          {formatMoney(selfTotal)}
        </div>
        <div className="text-[11px] text-[#4B4567] mt-0.5">
          {entryLabel(selfCount)}
        </div>
      </div>
      <div className="rounded-2xl border border-[#E5E0EE] bg-[#F5F1FB] p-4">
        <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#8471B3] mb-1">
          {coparentName || "Co-parent"}
        </div>
        <div
          className="font-serif text-2xl text-[#1A1330]"
          data-testid="cost-splitter-coparent-total"
        >
          {hasCompare ? formatMoney(coparentTotal) : "—"}
        </div>
        <div className="text-[11px] text-[#4B4567] mt-0.5">
          {hasCompare ? entryLabel(coparentCount) : "Not linked yet"}
        </div>
      </div>
      <div className="rounded-2xl border border-[#D6CFE8] bg-white p-4">
        <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">
          Combined
        </div>
        <div
          className="font-serif text-2xl text-[#1A1330]"
          data-testid="cost-splitter-combined-total"
        >
          {formatMoney(combinedTotal)}
        </div>
        <div className="text-[11px] text-[#4B4567] mt-0.5">
          {hasCompare ? "Both accounts tallied" : "Log more to see the split"}
        </div>
      </div>
    </div>
  );
}
