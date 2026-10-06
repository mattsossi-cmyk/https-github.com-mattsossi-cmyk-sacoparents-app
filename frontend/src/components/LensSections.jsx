import { PathwayList } from "@/components/LensScale";
import { QUESTION_OF_SECTION, SOURCE_OF_SECTION } from "@/components/ReportFraming";

export const REPORT_STEPS = ["Case & Assessment Overview", "Alignment Snapshot & Safety Screening", "Parent A Perspective", "Parent B Perspective", "Joint Co-Parenting Assessment", "Child-Focused Legal Issues", "Options & Resources", "Conflict Resolution Pathways", "Legal Conflict & Agreement-Building Analysis", "Professional Legal Statement & Roadmap", "Concise Court Summary"];

const TAG = { parent: ["Parent-Reported Information", "bg-align-blue/15 text-align-blue"], system: ["System-Generated Comparison", "bg-brand-purple/10 text-brand-purple"], professional: ["Professional Observation", "bg-align-green/15 text-green-900"], ai: ["AI-Assisted Draft", "bg-align-yellow/25 text-yellow-900"], safety: ["Separate Safety Pathway", "bg-red-50 text-red-700"] };
export function SourceTag({ kind }) {
  const [label, cls] = TAG[kind];
  return <span className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${cls}`} data-testid={`lens-source-${kind}`}>{label}</span>;
}
export const SOURCE_TAG = TAG;

export function ReportHeader({ title = "Professional Alignment Report", subtitle, right }) {
  return (
    <div className="rounded-lg border-b-4 border-brand-purple bg-white p-6 sm:p-8" data-testid="lens-report-header">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="h-11 w-11 shrink-0 rounded-full" style={{ background: "linear-gradient(90deg,#5b2d8e 50%,#1f9a94 50%)" }} aria-hidden="true" />
          <div><p className="text-2xl font-extrabold leading-tight text-brand-purple">SA CoParents <span className="text-teal-600">Align</span></p><p className="text-xs font-bold text-align-blue">Starting With Alignment, Ending With Agreement</p></div>
        </div>
        <div className="flex flex-col items-end gap-2"><p className="text-right text-[10px] font-extrabold uppercase leading-relaxed tracking-[0.08em] text-brand-purple">Child Focused<br />Solutions<br />Stronger Tomorrows</p>{right}</div>
      </div>
      <h1 className="mt-5 text-3xl font-bold text-brand-purple" data-testid="lens-title">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm text-muted-foreground">{subtitle || "A structured review of individual and joint parent assessments, child-focused concerns, areas of alignment and difference, available resources, and potential conflict-resolution pathways."}</p>
    </div>
  );
}

const CARD = { purple: "border-[#dcd7e6] bg-[#f3edfb] [&>h3]:text-brand-purple", teal: "border-[#dcd7e6] bg-[#e8f7f7] [&>h3]:text-teal-700", blue: "border-[#dcd7e6] bg-[#eaf4fb] [&>h3]:text-align-blue", green: "border-[#dcd7e6] bg-[#eaf7f1] [&>h3]:text-align-green", orange: "border-[#dcd7e6] bg-[#fff0e8] [&>h3]:text-[#d86936]", gold: "border-[#f0d78a] bg-[#fff7df] [&>h3]:text-[#b07d10]" };
export function LensCard({ tone = "purple", title, children, testId, className = "" }) {
  return <div className={`rounded-xl border p-4 ${CARD[tone]} ${className}`} data-testid={testId}><h3 className="text-sm font-bold">{title}</h3><div className="mt-2 space-y-1.5 text-sm">{children}</div></div>;
}

const PURPLE_SEC = ["bg-[#f3edfb] text-brand-purple", "bg-brand-purple"], BLUE_SEC = ["bg-[#eaf4fb] text-brand-blue", "bg-brand-blue"], TEAL_SEC = ["bg-[#e8f7f7] text-teal-700", "bg-brand-teal"];
export const SECTION_TINT = { 1: ["bg-slate-100 text-slate-600", "bg-slate-500"], 2: PURPLE_SEC, 3: PURPLE_SEC, 4: BLUE_SEC, 5: TEAL_SEC, 6: TEAL_SEC, 7: BLUE_SEC, 8: ["bg-[#eaf7f1] text-green-800", "bg-brand-green"],
  9: ["bg-[#fff0e8] text-orange-700", "bg-orange-600"], 10: BLUE_SEC, 11: ["bg-[#fff7df] text-yellow-800", "bg-yellow-600"] };

export function LensSec({ n, title, children, testId, id }) {
  const [head, badge] = SECTION_TINT[n] || PURPLE_SEC;
  const q = QUESTION_OF_SECTION[n], src = SOURCE_OF_SECTION[n];
  return (
    <section className="rounded-lg border border-border bg-white p-5 sm:p-6" data-testid={testId || `lens-${id}`} id={id}>
      <h2 className={`flex items-center gap-2 rounded-md px-3 py-2 text-lg font-semibold ${head}`}>{n !== undefined && <span className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${badge}`}>{n}</span>}{title}</h2>
      {q && <div className="mt-2 flex flex-wrap items-center justify-between gap-2 px-1" data-testid={`lens-sec-${n}-framing`}><p className="text-xs italic text-muted-foreground" data-testid={`lens-sec-${n}-question`}>{q}</p><SourceTag kind={src} /></div>}
      <div className="mt-4 space-y-3 text-sm leading-relaxed">{children}</div>
    </section>
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
          <div key={k} className={`rounded-md border p-2 ${v.checked ? "border-brand-teal/50 bg-brand-teal/5" : "border-border bg-white/60"}`} data-testid={`${testId}-${k}`}>
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
