/**
 * ActivitiesDimensionPrimitives.jsx — extracted from
 * `ActivitiesAlignment.jsx` (2026-03-06) to keep the page under
 * component-size budget.
 *
 * Two pure presentational primitives:
 *   - <ScoreBar />   — the coloured self/coparent progress bar.
 *   - <DimensionRow /> — a single dimension card with delta chip
 *                        and both parents' bars stacked.
 *
 * Both are stateless — they take rendered numbers only. No hooks, no
 * API calls. Callers own the layout and the data.
 */
import React from "react";

export function ScoreBar({ value, tone = "self" }) {
  const width = `${Math.min(100, Math.max(0, value || 0))}%`;
  const color = tone === "self" ? "bg-[#1E7A55]" : "bg-[#8471B3]";
  return (
    <div className="h-2 w-full bg-[#EEF5F0] rounded-full overflow-hidden">
      <div className={`h-full ${color}`} style={{ width }} />
    </div>
  );
}

export function DimensionRow({ row, coparentName }) {
  return (
    <div
      className="rounded-2xl border border-[#C7E5D3] bg-white p-4"
      data-testid={`activities-dim-${row.dimension}`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="font-serif text-lg text-[#1A1330] leading-tight">
            {row.label}
          </div>
          <p className="text-[0.75rem] text-[#4B4567] mt-0.5 leading-snug">
            {row.blurb}
          </p>
        </div>
        <div className="text-[0.6875rem] text-[#4B4567]">
          Delta:{" "}
          <span
            className={`font-semibold ${row.delta <= 15 ? "text-[#1E7A55]" : "text-[#904B0E]"}`}
          >
            {row.delta}
          </span>
        </div>
      </div>
      <div className="mt-3 grid gap-3">
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#1E7A55] mb-1">
            You · {row.self_score}
          </div>
          <ScoreBar value={row.self_score} tone="self" />
        </div>
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#6A5799] mb-1">
            {coparentName || "Co-parent"} · {row.coparent_score}
          </div>
          <ScoreBar value={row.coparent_score} tone="coparent" />
        </div>
      </div>
    </div>
  );
}
