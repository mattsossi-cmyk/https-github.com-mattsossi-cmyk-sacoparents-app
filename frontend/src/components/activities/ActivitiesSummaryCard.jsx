/**
 * ActivitiesSummaryCard.jsx — extracted from `ActivitiesAlignment.jsx`
 * (2026-03-06).
 *
 * Renders the "Neutral summary" card at the top of the ready state:
 *   - Eyebrow + AI-drafted pill (when a model is known).
 *   - Loading spinner while the LLM composes.
 *   - Final summary paragraph, or a graceful italic fallback if the
 *     LLM call short-circuited (unsafe intake or hard failure).
 *
 * Pure presentation — accepts summary text + summarising boolean +
 * model name from the parent page's state.
 */
import React from "react";
import { Loader2 } from "lucide-react";

import AIDraftedPill from "../AIDraftedPill";

export default function ActivitiesSummaryCard({
  summary,
  summaryModel,
  summarizing,
}) {
  return (
    <div className="rounded-3xl border border-[#C7E5D3] bg-white p-6 sm:p-7 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#1E7A55]">
          Neutral summary
        </span>
        {summary && summaryModel && (
          <AIDraftedPill
            model={summaryModel}
            tone="green"
            testId="activities-alignment-summary-pill"
          />
        )}
      </div>
      <h2 className="font-serif text-xl text-[#1A1330] leading-tight mb-3">
        What the two of you actually said
      </h2>
      {summarizing && (
        <div className="text-sm text-[#4B4567] inline-flex items-center gap-2">
          <Loader2 size={14} className="animate-spin" /> Composing a neutral summary…
        </div>
      )}
      {!summarizing && summary && (
        <p
          className="text-[15px] text-[#1A1330] leading-relaxed whitespace-pre-wrap"
          data-testid="activities-alignment-summary"
        >
          {summary}
        </p>
      )}
      {!summarizing && !summary && (
        <p className="text-sm text-[#4B4567] italic">
          Summary unavailable — the dimensions below still tell the story.
        </p>
      )}
    </div>
  );
}
