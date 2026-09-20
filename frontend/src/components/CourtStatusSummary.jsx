import { useState } from "react";
import { toast } from "sonner";
import { RefreshCw, Sparkles } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const LINES = [["current_status", "Current Status"], ["professional", "Professional"], ["parents", "Parents"], ["joint_assessment", "Joint Assessment"],
  ["professional_statement", "Professional Statement"], ["recent_communication", "Recent Communication"], ["outstanding", "Outstanding"], ["next_action", "Next Court-Facing Action"]];

export function CourtStatusSummary({ referralId, summary, onRefreshed, readOnly = false }) {
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    setBusy(true);
    try { const { data } = await api.post(`/court-dashboard/referrals/${referralId}/refresh-summary`); onRefreshed?.(data); toast.success("Status summary refreshed"); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };
  return (
    <div className="mt-3 rounded-lg border border-border bg-secondary/40 p-4" data-testid={`court-status-summary-${referralId}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-accent flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5" /> AI Current Status Summary
          {summary?.outdated && <span className="ml-1 rounded-full bg-align-yellow/40 px-2 py-0.5 text-[10px] font-bold text-yellow-950" data-testid={`court-summary-outdated-${referralId}`}>Outdated</span>}
        </p>
        {!readOnly && <Button size="sm" variant="outline" onClick={refresh} disabled={busy} className="h-7 text-xs gap-1" data-testid={`court-summary-refresh-${referralId}`}><RefreshCw className={`h-3 w-3 ${busy ? "animate-spin" : ""}`} /> {summary ? "Refresh" : "Generate"} status summary</Button>}
      </div>
      {summary ? (
        <>
          <dl className="mt-3 grid gap-1 text-sm">
            {LINES.map(([k, label]) => <div key={k} className="flex gap-2"><dt className="w-44 shrink-0 font-semibold text-foreground/80">{label}:</dt><dd data-testid={`court-summary-${k}-${referralId}`}>{summary[k]}</dd></div>)}
          </dl>
          <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground" data-testid={`court-summary-disclaimer-${referralId}`}>Generated {summary.generated_at?.slice(0, 16).replace("T", " ")}. {summary.disclaimer}</p>
        </>
      ) : <p className="mt-2 text-xs text-muted-foreground">No summary yet — generate one to see stage, completion and the next court-facing action.</p>}
    </div>
  );
}
