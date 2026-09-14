import { useState } from "react";
import { toast } from "sonner";
import { CalendarDays, AlertTriangle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CaseProgress } from "@/components/CaseProgress";
import { CourtStatusSummary } from "@/components/CourtStatusSummary";
import { CommunicationsLog } from "@/components/CommunicationsLog";

const Field = ({ label, children, testId }) => (
  <div className="min-w-0" data-testid={testId}>
    <p className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">{label}</p>
    <div className="mt-0.5 text-sm">{children}</div>
  </div>
);

function HearingDate({ x, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(x.hearing_date || "");
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.patch(`/court-dashboard/referrals/${x.id}/hearing-date`, { hearing_date: val });
      toast.success(data.hearing_date ? `Hearing date set: ${data.hearing_date}` : "Hearing date cleared");
      onSaved(data.hearing_date); setEditing(false);
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  if (editing) return (
    <div className="flex items-center gap-2" data-testid={`hearing-edit-${x.id}`}>
      <Input type="date" value={val} onChange={(e) => setVal(e.target.value)} className="h-8 w-44" data-testid={`hearing-input-${x.id}`} />
      <Button size="sm" onClick={save} disabled={busy} data-testid={`hearing-save-${x.id}`}>Save</Button>
      <Button size="sm" variant="ghost" onClick={() => setEditing(false)} data-testid={`hearing-cancel-${x.id}`}>Cancel</Button>
    </div>
  );
  return (
    <div className="flex items-center gap-2">
      <CalendarDays className="h-3.5 w-3.5 text-brand-purple" />
      <span data-testid={`hearing-value-${x.id}`}>{x.hearing_date || "Not set"}</span>
      <button type="button" onClick={() => setEditing(true)} className="text-xs text-primary hover:underline" data-testid={`hearing-edit-btn-${x.id}`}>{x.hearing_date ? "Change" : "Add hearing date"}</button>
    </div>
  );
}

export function CourtCaseCard({ x, packets, onOpenPacket, onUpdate }) {
  const stage = x.stage || {};
  const submitted = x.status === "submitted";
  const mine = (packets || []).filter((p) => p.cause_number && p.cause_number === x.cause_number);
  return (
    <li className={`px-5 py-5 space-y-4 ${x.overdue ? "border-l-4 border-l-red-500" : ""}`} data-testid={`court-referral-row-${x.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-lg font-semibold">Cause No. {x.cause_number}{x.case_code && <span className="ml-2 text-sm font-normal tracking-wider text-muted-foreground">{x.case_code}</span>}</p>
        <span className="text-xs text-muted-foreground">referred {x.created_at?.slice(0, 10)}</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Assigned Professional" testId={`court-field-pro-${x.id}`}><span className="font-medium">{x.professional_name}</span>{x.status === "pending" && <span className="ml-1 text-xs text-muted-foreground">(awaiting acceptance)</span>}{x.status === "declined" && <span className="ml-1 text-xs text-red-700">Declined: {x.decline_reason}</span>}</Field>
        <Field label="Current Status" testId={`court-field-status-${x.id}`}><span className="font-medium">{stage.label || x.status}</span></Field>
        <Field label="Hearing Date" testId={`court-field-hearing-${x.id}`}>
          <HearingDate x={x} onSaved={(hd) => onUpdate({ ...x, hearing_date: hd })} />
          {x.overdue && <p className="mt-1 inline-flex items-center gap-1 rounded-md bg-red-50 px-2 py-0.5 text-xs font-bold text-red-700" data-testid={`court-overdue-${x.id}`}><AlertTriangle className="h-3.5 w-3.5" /> Hearing within 7 days — nothing submitted</p>}
        </Field>
        <Field label="Joint Assessment Status" testId={`court-field-joint-${x.id}`}>{(stage.index ?? 0) >= 3 ? "Both parents complete" : (stage.index ?? 0) >= 2 ? "Parents invited — in progress" : "Not started"}
          {(x.requested_reports || []).length > 0 && <p className="mt-1 text-xs text-muted-foreground" data-testid={`court-field-requested-${x.id}`}>Requested: {x.requested_reports.map((r) => r.label).join(" · ")}</p>}
        </Field>
      </div>
      <CaseProgress stage={stage} />
      <CourtStatusSummary referralId={x.id} summary={x.status_summary} onRefreshed={(s) => onUpdate({ ...x, status_summary: s })} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Final Joint Reports & Professional Statements" testId={`court-field-submissions-${x.id}`}>
          {mine.length === 0 ? <span className="text-muted-foreground">{submitted ? "Submitted — see Court Packets below." : "Nothing submitted yet."}</span> : (
            <ul className="space-y-1">{mine.map((p) => (
              <li key={p.id} className="flex items-center gap-2"><span>{p.subject_label} · {p.created_at?.slice(0, 10)}</span><button type="button" onClick={() => onOpenPacket(p)} className="text-xs text-primary hover:underline" data-testid={`court-open-submission-${p.id}`}>Open</button></li>
            ))}</ul>
          )}
        </Field>
        <Field label="Professional Communications & Audit" testId={`court-field-audit-${x.id}`}>
          <span className="text-muted-foreground">{x.submissions ? `${x.submissions} submission version${x.submissions === 1 ? "" : "s"} on record. ` : ""}Open a packet to view its audit history.</span>
          <div className="mt-2"><CommunicationsLog url={`/court-dashboard/referrals/${x.id}/communications`} title="Court-facing notices" compact /></div>
        </Field>
      </div>
    </li>
  );
}
