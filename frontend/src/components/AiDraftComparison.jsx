import { useState } from "react";
import { ChevronDown, ChevronRight, Sparkles } from "lucide-react";

const TITLES = { safety_takeaway: "Safety takeaway", parent_a_growth: "Parent A key growth areas", parent_b_growth: "Parent B key growth areas", joint_notes: "Joint dynamic summary", conflict_management_rationale: "Conflict resolution rationale", short_term_goals: "Short-term goals", long_term_goals: "Long-term goals", alignment_summary: "Professional alignment summary", professional_summary: "Professional summary" };

export function AiDraftComparison({ drafts, rep }) {
  const [open, setOpen] = useState(false);
  const keys = Object.keys(drafts || {});
  if (!keys.length) return null;
  const edited = keys.filter((k) => (rep[k] || "").trim() !== drafts[k].text.trim());
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50/60" data-testid="ai-comparison">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 p-3 text-left text-sm font-semibold" data-testid="ai-comparison-toggle">
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}<Sparkles className="h-4 w-4 text-amber-600" />
        AI draft vs. your final text — {keys.length} AI-assisted section{keys.length === 1 ? "" : "s"}, {edited.length} edited
        <span className="ml-auto text-xs font-normal text-muted-foreground">Recorded in the audit log and the PDF disclosure appendix</span>
      </button>
      {open && <ul className="space-y-3 p-3 pt-0" data-testid="ai-comparison-list">
        {keys.map((k) => {
          const isEdited = edited.includes(k);
          return (
            <li key={k} className="rounded-md border border-border bg-white p-3" data-testid={`ai-compare-${k}`}>
              <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground flex items-center gap-2">{TITLES[k] || k}
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${isEdited ? "bg-align-green/15 text-align-green" : "bg-amber-100 text-amber-800"}`} data-testid={`ai-compare-${k}-state`}>{isEdited ? "Edited by you" : "Unchanged — review required"}</span>
                <span className="ml-auto font-normal normal-case tracking-normal">{drafts[k].model} · {String(drafts[k].at).slice(0, 10)}</span></p>
              <div className="mt-2 grid gap-3 sm:grid-cols-2 text-sm">
                <div><p className="text-[11px] font-semibold text-amber-700">AI draft</p><p className="whitespace-pre-wrap text-muted-foreground">{drafts[k].text}</p></div>
                <div><p className="text-[11px] font-semibold text-brand-purple">Your current text</p><p className="whitespace-pre-wrap">{rep[k] || <em className="text-muted-foreground">empty</em>}</p></div>
              </div>
            </li>
          );
        })}
      </ul>}
    </div>
  );
}
