import React from "react";
import { CheckCircle2, ExternalLink, ShieldCheck, Zap } from "lucide-react";

import { useCaseSettings } from "../../lib/useCaseSettings";
import { useCheckinLink } from "../../lib/useCheckinLink";

const DEFAULT_TEXT = "Before you choose your journey, take your private Family check-in. Your co-parent never sees your answers.";

// Shown until SACOparentsAlign confirms the Family check-in is done.
export function SafetyFirstBanner({ alignUrl, onQuickExit, testid = "safety-first-banner", text = DEFAULT_TEXT }) {
  const done = useCaseSettings()?.setup_complete === true;
  const href = useCheckinLink(alignUrl);
  if (done) {
    return (
      <p data-testid={`${testid}-done`} className="flex items-center justify-center gap-1.5 rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2 text-xs font-bold text-emerald-800">
        <CheckCircle2 size={14} aria-hidden="true" /> Safety step: completed
      </p>
    );
  }
  return (
    <section data-testid={testid} aria-labelledby={`${testid}-title`} className="rounded-2xl border-2 border-[#C28771]/40 bg-[#FBF3EE] p-4 text-left">
      <div className="flex items-start gap-3">
        <span className="shrink-0 w-10 h-10 rounded-xl bg-[#C28771]/15 text-[#9A5D47] grid place-items-center" aria-hidden="true">
          <ShieldCheck size={20} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 id={`${testid}-title`} className="text-sm font-extrabold text-[#5a2a18]">Safety first</h2>
          <p data-testid={`${testid}-text`} className="text-[0.8125rem] text-[#4B4567] mt-0.5 leading-snug">
            {text}
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <a href={href || undefined} aria-disabled={!href} target="_blank" rel="noopener noreferrer" data-testid={`${testid}-checkin`}
           className={`inline-flex items-center gap-1.5 min-h-[40px] rounded-full bg-[#4a2574] px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-[#3a1d5c] ${href ? "" : "opacity-60 pointer-events-none"}`}>
          Open Family check-in <ExternalLink size={12} aria-hidden="true" /><span className="sr-only"> (opens in a new tab)</span>
        </a>
        <button type="button" onClick={onQuickExit} data-testid={`${testid}-quick-exit`}
                className="inline-flex items-center gap-1 min-h-[40px] rounded-full bg-rose-600 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-rose-700">
          <Zap size={12} aria-hidden="true" /> Quick exit
        </button>
      </div>
      <p data-testid={`${testid}-help`} className="mt-2.5 text-[0.6875rem] text-[#4B4567]">
        In danger? Call <a href="tel:911" className="font-bold underline">911</a>. National DV Hotline:{" "}
        <a href="tel:18007997233" className="font-bold underline">1-800-799-7233</a>
      </p>
    </section>
  );
}
