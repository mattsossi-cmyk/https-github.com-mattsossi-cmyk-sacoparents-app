import React, { useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { ArchiveLink } from "./ArchiveLink";
import { NudgeButton } from "./NudgeButton";
import { ProgressPdfButton } from "./ProgressPdfButton";
import { RequestedProgress, fmtDay } from "./RequestedProgress";

export const stateOf = (c) => (c.revoked_at ? "Revoked" : c.expires_at && new Date(c.expires_at) < new Date() ? "Expired" : "Active");

// Finished = revoked, expired, or every linked parent done (matches the server's "Archive finished").
export const isFinishedCode = (c) =>
  stateOf(c) !== "Active" || (c.parents.length > 0 && c.parents.every((p) => p.assessments.every((r) => r.status === "done")));

export const CourtCodeItem = ({ c, onChanged }) => {
  const [busy, setBusy] = useState(false);
  const state = stateOf(c);
  const revoke = async () => {
    if (!window.confirm(`Revoke ${c.case_id}? Parents who haven't entered the code yet won't be able to use it.`)) return;
    setBusy(true);
    try {
      await api.post(`/professional/court-codes/${c.case_id}/revoke`);
      toast.success(`${c.case_id} revoked`);
      onChanged();
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || "Revoke failed"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className={`rounded-xl border border-[#E5E0EE] p-3 ${c.archived_at ? "bg-[#F4F2F8] opacity-80" : "bg-[#FAF8FD]"}`} data-testid={`court-code-row-${c.case_id}`}>
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <div className="min-w-0 text-xs text-[#4B4567]">
          <span className="font-mono text-sm font-semibold text-[#1A1330] mr-2">{c.case_id}</span>
          <span className={`font-bold ${state === "Active" ? "text-[#1F5C3B]" : "text-[#B02A2A]"}`} data-testid={`court-code-state-${c.case_id}`}>{state}</span>
          {c.label ? ` · ${c.label}` : ""}
          {c.expires_at && state === "Active" ? ` · until ${fmtDay(c.expires_at)}` : ""}
          {c.archived_at ? <span className="ml-1 font-semibold text-[#857E9C]" data-testid={`court-code-archived-${c.case_id}`}>· Archived</span> : null}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <ProgressPdfButton path={`/professional/court-codes/${c.case_id}/progress.pdf`} caseId={c.case_id} testid={`court-code-progress-pdf-${c.case_id}`} />
          {state === "Active" && (
            <button type="button" onClick={revoke} disabled={busy} data-testid={`court-code-revoke-${c.case_id}`}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#B02A2A] hover:underline disabled:opacity-60">
              {busy ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />} Revoke
            </button>
          )}
          <ArchiveLink caseRef={c.case_id} archived={!!c.archived_at} onChanged={onChanged} testid={`court-code-archive-${c.case_id}`} />
        </div>
      </div>
      {c.parents.length === 0 ? (
        <p className="text-[11px] text-[#857E9C] mt-2" data-testid={`court-code-waiting-${c.case_id}`}>No parent has entered this code yet.</p>
      ) : (
        <div className="mt-1 grid gap-2 sm:grid-cols-2">
          {c.parents.map((p, i) => (
            <div key={i} className="rounded-lg border border-[#E5E0EE] bg-white p-2.5" data-testid={`court-code-parent-${c.case_id}-${i}`}>
              <div className="text-sm text-[#1A1330] truncate">{p.name}</div>
              <RequestedProgress rows={p.assessments} testid={`court-code-progress-${c.case_id}-${i}`} />
              <NudgeButton caseRef={c.case_id} pid={p.pid} nextAt={p.nudge_next_at} lastAt={p.nudge_last_at} count={p.nudge_count} rows={p.assessments} testid={`court-code-nudge-${c.case_id}-${i}`} />
            </div>
          ))}
        </div>
      )}
    </li>
  );
};
