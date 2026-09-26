import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const BADGE = {
  Complete: "bg-align-green/15 text-green-900", Available: "bg-align-green/15 text-green-900", Submitted: "bg-align-green/15 text-green-900",
  "Ready for Review": "bg-brand-purple/10 text-brand-purple", Pending: "bg-align-yellow/30 text-yellow-900", "In Progress": "bg-align-yellow/30 text-yellow-900",
  "Awaiting acceptance": "bg-align-yellow/30 text-yellow-900", Declined: "bg-red-50 text-red-700", "Not Ready": "bg-secondary text-muted-foreground",
};

export function StatusBadge({ status, testId }) {
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${BADGE[status] || "bg-secondary text-muted-foreground"}`} data-testid={testId}>{status}</span>;
}

export function PortalCard({ title, children, testId, action }) {
  return (
    <div className="rounded-2xl border border-border bg-white p-5 shadow-sm" data-testid={testId}>
      <div className="mb-4 flex items-center justify-between gap-3"><h3 className="text-lg font-semibold text-brand-purple">{title}</h3>{action}</div>
      {children}
    </div>
  );
}

export const caseStatus = (x) => {
  if (x.status === "declined") return "Declined";
  if (x.status === "pending") return "Awaiting acceptance";
  const idx = x.stage?.index ?? 0;
  return idx >= 6 ? "Submitted" : idx >= 5 ? "Ready for Review" : "In Progress";
};

export function CaseSidebar({ refs, selectedId, onSelect, search, setSearch }) {
  const term = search.toLowerCase().trim();
  const shown = refs.filter((x) => !term || [x.cause_number, x.case_code, x.professional_name].some((v) => (v || "").toLowerCase().includes(term)));
  return (
    <PortalCard title="Court Cases" testId="court-case-sidebar">
      <input type="text" placeholder="Search cause no., case ID or professional" value={search} onChange={(e) => setSearch(e.target.value)} data-testid="court-case-search"
        className="mb-4 w-full rounded-xl border border-border px-4 py-3 text-sm outline-none focus:border-brand-purple" />
      <div className="space-y-3">
        {shown.length === 0 && <p className="text-sm text-muted-foreground" data-testid="court-case-search-empty">No cases match.</p>}
        {shown.map((x) => (
          <button key={x.id} type="button" onClick={() => onSelect(x.id)} data-testid={`court-case-pick-${x.id}`}
            className={`w-full rounded-xl border p-4 text-left transition-colors ${selectedId === x.id ? "border-brand-purple bg-brand-purple/5" : x.overdue ? "border-red-200 bg-red-50/40 hover:border-brand-purple/50" : "border-border bg-white hover:border-brand-purple/50"}`}>
            <div className="font-semibold text-foreground">Cause No. {x.cause_number}</div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground">{x.case_code || "—"}{x.child_initials ? ` · Child ${x.child_initials}` : ""}</div>
            <div className="mt-1 text-sm text-muted-foreground">{x.professional_name}</div>
            <div className="mt-3 flex flex-wrap items-center gap-2"><StatusBadge status={caseStatus(x)} />{x.hearing_date && <span className={`text-xs ${x.overdue ? "font-semibold text-red-700" : "text-muted-foreground"}`}>Hearing {x.hearing_date}</span>}</div>
          </button>
        ))}
      </div>
    </PortalCard>
  );
}

const Field = ({ label, value, testId }) => <div><div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div><div className="mt-1 font-semibold" data-testid={testId}>{value || "—"}</div></div>;

export function CaseOverview({ x, d, hearing }) {
  return (
    <PortalCard title="Case Overview" testId="court-overview">
      <div className="grid gap-4 md:grid-cols-3">
        <Field label="Cause Number" value={x.cause_number} testId="court-overview-cause" />
        <Field label="SA CoParents Case ID" value={x.case_code} testId="court-overview-case-id" />
        <Field label="Assigned Professional" value={x.professional_name} testId="court-overview-pro" />
        <Field label="Parties' ZIP" value={x.parties_zip ? `${x.parties_zip}${x.professional_distance_miles != null ? ` · professional ≈ ${x.professional_distance_miles} mi away` : ""}` : ""} testId="court-overview-zip" />
        <Field label="Court" value={x.court_name} />
        <Field label="Child" value={x.child_initials} />
        <Field label="Stage" value={d?.stage?.label || x.stage?.label} testId="court-overview-stage" />
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <StatusBadge status={caseStatus(x)} testId="court-overview-status" />
        <span className="text-xs text-muted-foreground">Hearing date:</span>{hearing}
        {x.overdue && <span className="text-xs font-bold text-red-700">Within 7 days — nothing submitted</span>}
      </div>
    </PortalCard>
  );
}

export function ParentStatus({ x, d }) {
  const focused = (x.requested_reports || []).filter((r) => r.key !== "co_parenting").map((r) => r.label);
  const done = (label) => d?.checklist?.find((c) => c.label === label)?.done;
  const parents = [["Parent A", x.parent_a_name, done("Parent A completed assessment")], ["Parent B", x.parent_b_name, done("Parent B completed assessment")]];
  return (
    <PortalCard title="Parent Assessment Status" testId="court-parent-status">
      <div className="grid gap-4 md:grid-cols-2">
        {parents.map(([label, name, ok], i) => (
          <div key={label} className="rounded-xl border border-border p-4" data-testid={`court-parent-${i ? "b" : "a"}`}>
            <div className="flex items-center justify-between"><h4 className="font-semibold">{label}{name ? ` · ${name}` : ""}</h4><StatusBadge status={!x.case_id ? "Not Ready" : ok ? "Complete" : "Pending"} /></div>
            <div className="mt-4 text-sm text-muted-foreground">Co-Parenting Assessment</div>
            {focused.length > 0 && <div className="mt-3"><div className="text-xs uppercase tracking-wide text-muted-foreground">Focused Assessments</div>
              <div className="mt-2 flex flex-wrap gap-2">{focused.map((f) => <span key={f} className="rounded-lg bg-brand-purple/5 px-3 py-1 text-xs font-medium text-brand-purple">{f}</span>)}</div></div>}
          </div>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">Completion status only — raw parent answers are never shown to the court.</p>
    </PortalCard>
  );
}

function ReportRow({ title, description, status, actionLabel, to, testId }) {
  const ready = status === "Available";
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border p-4 md:flex-row md:items-center md:justify-between" data-testid={testId}>
      <div><div className="flex flex-wrap items-center gap-3"><h4 className="font-semibold">{title}</h4><StatusBadge status={status} /></div><p className="mt-2 max-w-2xl text-sm text-muted-foreground">{description}</p></div>
      {ready ? <Button asChild className="bg-brand-purple text-white hover:bg-brand-purple/90" data-testid={`${testId}-open`}><Link to={to}>{actionLabel}</Link></Button>
        : <Button disabled variant="secondary" data-testid={`${testId}-open`}>{actionLabel}</Button>}
    </div>
  );
}

export function ReportsAvailable({ x, d }) {
  const submitted = (d?.reports?.length || 0) > 0;
  const base = `/court/case/${x.id}`;
  return (
    <PortalCard title="Reports Available to the Court" testId="court-reports-available">
      <div className="space-y-4">
        <ReportRow title="Joint Parent Assessment Report" description="Side-by-side presentation of areas of alignment and differing parent perspectives." status={submitted ? "Available" : "Not Ready"} actionLabel="Review Joint Report" to={`${base}#reports`} testId="court-report-joint" />
        <ReportRow title="Professional Report" description="Professional interpretation, options, resources, and child-focused observations." status={d?.statement ? "Available" : "Not Ready"} actionLabel="Review Professional Report" to={`${base}#statement`} testId="court-report-professional" />
        <ReportRow title="Court Status Summary" description="Concise summary of assessment completion, reports received, and current case status." status={x.case_id ? "Available" : "Not Ready"} actionLabel="View Court Summary" to={`${base}#summary`} testId="court-report-summary" />
      </div>
    </PortalCard>
  );
}

export function HowItWorks() {
  const steps = ["Refer a case to an approved professional (cause number + both parents).", "The professional invites both parents; each completes a private assessment.", "The Joint Report and Professional Report return to you through Align as frozen, hash-sealed submissions.", "Use the case thread for status and clarification requests only — never raw parent answers."];
  return (
    <PortalCard title="How the Judicial Portal works" testId="court-how-it-works">
      <ol className="space-y-2 text-sm">{steps.map((s, i) => <li key={i} className="flex gap-3"><span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{i + 1}</span><span>{s}</span></li>)}</ol>
    </PortalCard>
  );
}
