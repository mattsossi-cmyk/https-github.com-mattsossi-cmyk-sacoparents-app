import { PathwayList } from "@/components/LensScale";

export const REPORT_STEPS = ["Case & Assessment Overview", "Individual Parent Perspectives", "Joint Assessment Findings", "Child-Focused Issues", "Options & Resources", "Conflict Resolution Pathways", "Professional Statement"];

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
      <div className="rounded-md border border-border bg-white p-3" data-testid="lens-conflict-guidance">
        <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Which pathway fits which kind of conflict?</p>
        <ul className="mt-1 space-y-1 text-xs">{(lib.conflict_guidance || []).map(([t, d]) => <li key={t}><strong>{t}:</strong> {d}</li>)}</ul>
      </div>
    </div>
  );
}
