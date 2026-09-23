import { PathwayList } from "@/components/LensScale";

export const REPORT_STEPS = ["Case & Assessment Overview", "Individual Parent Perspectives", "Joint Assessment Findings", "Child-Focused Issues", "Options & Resources", "Conflict Resolution", "Professional Statement", "Concise Court / Referral Summary"];

const TAG = { parent: ["Parent-Reported Information", "bg-align-blue/15 text-align-blue"], system: ["System-Generated Comparison", "bg-brand-purple/10 text-brand-purple"], professional: ["Professional Observation", "bg-align-green/15 text-green-900"], safety: ["Separate Safety Pathway", "bg-red-50 text-red-700"] };
export function SourceTag({ kind }) {
  const [label, cls] = TAG[kind];
  return <span className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${cls}`} data-testid={`lens-source-${kind}`}>{label}</span>;
}

export function ReportHeader({ title = "Professional Alignment Report", subtitle, right }) {
  return (
    <div className="rounded-lg bg-gradient-to-br from-[#4f2d8c] to-[#6f42c1] p-8 text-white" data-testid="lens-report-header">
      <p className="text-xs font-bold uppercase tracking-[0.08em] opacity-90">SA CoParents Align</p>
      <div className="flex flex-wrap items-start justify-between gap-3"><h1 className="mt-1 text-3xl font-bold" data-testid="lens-title">{title}</h1>{right}</div>
      <p className="mt-2 max-w-3xl text-sm opacity-90">{subtitle || "A structured review of individual and joint parent assessments, child-focused concerns, areas of alignment and difference, available resources, and potential conflict-resolution pathways."}</p>
    </div>
  );
}

export function SafetyPathwayCard({ notes }) {
  const [t, d] = notes.safety_pathway || [];
  return <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4" data-testid="lens-safety-pathway"><SourceTag kind="safety" /><h3 className="mt-1 font-semibold text-red-700">{t}</h3><p className="mt-1 text-sm">{d}</p></div>;
}

export function ReportDisclaimer({ notes, signature, date }) {
  return (
    <div className="space-y-4" data-testid="lens-disclaimer">
      <div className="grid gap-8 sm:grid-cols-2 pt-6"><div className="border-t border-foreground/70 pt-1 text-xs text-muted-foreground">Professional Name / Signature{signature ? <span className="block font-semibold text-foreground">{signature}</span> : null}</div><div className="border-t border-foreground/70 pt-1 text-xs text-muted-foreground">Date{date ? <span className="block font-semibold text-foreground">{date}</span> : null}</div></div>
      <p className="rounded-md bg-secondary/60 p-3 text-xs text-muted-foreground"><strong>Important:</strong> {notes.disclaimer}</p>
    </div>
  );
}

export function AlignmentStatusGrid({ rep }) {
  const cells = [["Areas of Alignment", rep.alignment_agreements || rep.joint_strengths, "bg-align-green/10 border-align-green/30"], ["Partial Alignment", rep.partial_alignment, "bg-align-yellow/20 border-align-yellow/60"], ["Different Perspectives", rep.alignment_disagreements || rep.joint_gaps, "bg-red-50 border-red-200"]];
  return <div className="grid gap-3 sm:grid-cols-3" data-testid="lens-status-grid">{cells.map(([t, v, cls]) => <div key={t} className={`rounded-lg border p-3 text-sm ${cls}`}><strong className="block mb-1">{t}</strong><span className="whitespace-pre-wrap">{v || "—"}</span></div>)}</div>;
}

export function ReportPrinciple({ notes, testId = "lens-principle" }) {
  return (
    <div className="rounded-md border border-brand-purple/20 bg-white p-4 text-sm" data-testid={testId}>
      <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Report principle</p>
      <ul className="mt-1 grid gap-1 sm:grid-cols-2">{(notes.principle || []).map((p) => <li key={p} className="pl-4 relative before:absolute before:left-0 before:content-['•']">{p}</li>)}</ul>
      <p className="mt-2 text-xs italic text-muted-foreground"><strong>Purpose:</strong> {notes.purpose}</p>
    </div>
  );
}

export function ChildFocusList({ categories = [], value = {}, onChange, testId = "lens-child-focus" }) {
  const upd = (k, patch) => onChange({ ...value, [k]: { checked: false, note: "", ...(value[k] || {}), ...patch } });
  return (
    <div className="grid gap-2 sm:grid-cols-2" data-testid={testId}>
      {categories.map(([k, label]) => {
        const v = value[k] || {};
        return (
          <div key={k} className={`rounded-md border p-2 ${v.checked ? "border-brand-purple/50 bg-white" : "border-border bg-white/60"}`} data-testid={`${testId}-${k}`}>
            <label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" checked={!!v.checked} onChange={(e) => upd(k, { checked: e.target.checked })} data-testid={`${testId}-${k}-check`} />{label}</label>
            {v.checked && <input value={v.note || ""} onChange={(e) => upd(k, { note: e.target.value })} placeholder="Optional note (neutral, child-focused)" className="mt-1 h-8 w-full rounded-md border border-input px-2 text-xs" data-testid={`${testId}-${k}-note`} />}
          </div>
        );
      })}
    </div>
  );
}

export function ChildFocusSummary({ categories = [], value = {}, testId }) {
  const items = categories.filter(([k]) => value[k]?.checked);
  if (!items.length) return <p className="text-sm italic text-muted-foreground" data-testid={testId}>No child-focused categories identified.</p>;
  return <ul className="list-disc pl-5 space-y-1" data-testid={testId}>{items.map(([k, label]) => <li key={k}><strong>{label}</strong>{value[k].note ? ` — ${value[k].note}` : ""}</li>)}</ul>;
}

export function PathwayPicker({ lib, rep, cls, set, readOnly = false }) {
  const chosen = rep.conflict_pathways || (rep.conflict_pathway ? [rep.conflict_pathway] : []);
  const toggle = (k) => set("conflict_pathways", chosen.includes(k) ? chosen.filter((x) => x !== k) : [...chosen, k]);
  return (
    <div className="space-y-3">
      <PathwayList pathways={lib.pathways} rating={rep.joint_rating} recommended={cls.joint?.pathway?.key} chosen={chosen} onToggle={readOnly ? undefined : toggle} />
      <SafetyPathwayCard notes={lib.notes || {}} />
      <div className="rounded-md border border-border bg-white p-3" data-testid="lens-conflict-guidance">
        <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Which pathway fits which kind of conflict?</p>
        <ul className="mt-1 space-y-1 text-xs">{(lib.conflict_guidance || []).map(([t, d]) => <li key={t}><strong>{t}:</strong> {d}</li>)}</ul>
      </div>
    </div>
  );
}
