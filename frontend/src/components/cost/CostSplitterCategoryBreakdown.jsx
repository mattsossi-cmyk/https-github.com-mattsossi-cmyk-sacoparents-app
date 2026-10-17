/**
 * cost/CostSplitterCategoryBreakdown.jsx — extracted from
 * `CostSplitterPanel.jsx` (2026-03-06).
 *
 * Renders the "By category" stacked bar breakdown. Hides itself if
 * there are no categories to render. Also owns the `CategoryBar`
 * sub-primitive that previously lived inline in the panel.
 */
import React from "react";

function formatMoney(cents) {
  const n = (cents || 0) / 100;
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function CategoryBar({ selfCents, coparentCents }) {
  const total = selfCents + coparentCents || 1;
  const selfPct = Math.round((selfCents / total) * 100);
  const coparentPct = 100 - selfPct;
  return (
    <div className="flex h-2 w-full rounded-full overflow-hidden bg-[#EEF5F0]">
      <div style={{ width: `${selfPct}%` }} className="bg-[#1E7A55]" />
      <div style={{ width: `${coparentPct}%` }} className="bg-[#8471B3]" />
    </div>
  );
}

export default function CostSplitterCategoryBreakdown({ perCategory, hasCompare }) {
  if (!perCategory || perCategory.length === 0) return null;
  return (
    <div className="mb-5">
      <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#4B4567] mb-2">
        By category
      </div>
      <div className="grid gap-2" data-testid="cost-splitter-categories">
        {perCategory.map((cat) => (
          <div
            key={cat.key}
            className="grid grid-cols-[1fr_auto] gap-3 items-center"
          >
            <div>
              <div className="text-sm text-[#1A1330]">{cat.label}</div>
              <CategoryBar
                selfCents={cat.self_cents || 0}
                coparentCents={cat.coparent_cents || 0}
              />
            </div>
            <div className="text-right">
              <div className="text-xs text-[#1E7A55] font-semibold">
                {formatMoney(cat.self_cents || 0)}
              </div>
              <div className="text-[0.6875rem] text-[#6A5799]">
                {hasCompare ? formatMoney(cat.coparent_cents || 0) : ""}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
