import { Link } from "react-router-dom";
import { Lock } from "lucide-react";

export const Sec = ({ n, title, children, testId }) => (
  <section className="bg-white border border-border rounded-lg p-6" data-testid={testId}>
    <h2 className="text-lg font-semibold flex items-center gap-2"><span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{n}</span>{title}</h2>
    <div className="mt-3 space-y-3 text-sm leading-relaxed">{children}</div>
  </section>
);
const Bullets = ({ label, items, empty = "None identified." }) => (
  <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</p>
    {items?.length ? <ul className="mt-1 space-y-1">{items.map((x, i) => <li key={i} className="pl-4 relative before:absolute before:left-0 before:content-['•']">{x}</li>)}</ul> : <p className="italic text-muted-foreground">{empty}</p>}
  </div>
);
const ParentBlock = ({ title, summary, testId }) => (
  <div className="rounded-md border border-border p-4" data-testid={testId}>
    <p className="font-semibold">{title}</p>
    <p className="mt-1 inline-block rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold tracking-widest text-amber-900">{summary?.label || "PARENT-REPORTED INFORMATION"}</p>
    <dl className="mt-2 space-y-2">{(summary?.items || []).map((it, i) => <div key={i}><dt className="text-xs font-semibold text-muted-foreground">{it.heading}</dt><dd>{it.text}</dd></div>)}</dl>
  </div>
);

export function LegalGeneratedSections({ data, start = 1 }) {
  const d = data.report?.legal_draft || {};
  const j = d.joint || {};
  const c = data.case || {};
  const court = c.court || {};
  const info = [["Case ID", c.case_code], ["Court case number", court.cause_number], ["Professional", data.professional?.name], ["Professional role", data.report?.role || data.professional?.pro_role],
    ["Parent A", c.parent_a], ["Parent B", c.parent_b], ["Children", data.is_sample ? c.child_name : (c.child_name ? `${c.child_name[0]}.` : "")], ["Date generated", (d.generated_at || "").slice(0, 10)], ["Report status", data.is_sample ? "SAMPLE ONLY" : data.status]];
  return (
    <>
      <Sec n={start} title="Case Information" testId="legal-s1"><dl className="grid gap-2 sm:grid-cols-3">{info.filter(([, v]) => v).map(([k, v]) => <div key={k}><dt className="text-xs text-muted-foreground">{k}</dt><dd className="font-medium">{v}</dd></div>)}</dl></Sec>
      <Sec n={start + 1} title="Purpose of Report" testId="legal-s2"><p className="italic">{data.purpose}</p></Sec>
      <Sec n={start + 2} title="Information Reviewed" testId="legal-s3"><Bullets label="Records that exist in this case" items={data.information_reviewed} empty="No records were available." /></Sec>
      <Sec n={start + 3} title="Individual Parent Assessment Summary" testId="legal-s4">
        <p className="text-xs italic text-muted-foreground">Parent-reported information. Disputed allegations are not presented as established facts. Visible to the assigned professional only.</p>
        <div className="grid gap-3 md:grid-cols-2"><ParentBlock title={`Parent A — ${c.parent_a || ""}`} summary={d.parent_a_summary} testId="legal-parent-a" /><ParentBlock title={`Parent B — ${c.parent_b || ""}`} summary={d.parent_b_summary} testId="legal-parent-b" /></div>
      </Sec>
      <Sec n={start + 4} title="Joint Assessment Findings" testId="legal-s5">
        {j.available ? <div className="grid gap-3 md:grid-cols-2"><Bullets label="Areas of alignment" items={j.alignment} /><Bullets label="Areas of difference" items={j.differences} /><Bullets label="Unresolved issues" items={j.unresolved} /><Bullets label="Shared child-focused priorities" items={j.shared_priorities} /><Bullets label="Potential areas for agreement" items={j.potential_agreement} /></div>
          : <p className="italic text-muted-foreground" data-testid="legal-no-joint">{j.note || "No completed Joint Assessment was available at the time this draft was generated."}</p>}
      </Sec>
      <Sec n={start + 5} title="Child-Focused Issues" testId="legal-s6"><Bullets label="Subjects supported by case information" items={(d.child_focused_summary || []).map((x) => `${x.topic}: ${x.text}`)} empty="No child-specific subjects were available." /></Sec>
      <Sec n={start + 6} title="Communication and Conflict Patterns" testId="legal-s7"><Bullets label="Reported patterns (no diagnosis, no labels)" items={(d.communication_summary || []).map((x) => `${x.pattern}: ${x.text}`)} /></Sec>
    </>
  );
}

const LENS = [["observations", "Professional Observations"], ["further_attention", "Issues Requiring Attention"], ["alignment_areas", "Areas of Existing Agreement"], ["partial_alignment", "Areas Appropriate for Further Agreement Building"], ["procedural_considerations", "Procedural Considerations"], ["professional_comments", "Other Professional Comments"]];

export function LegalReadOnlyTail({ data, start = 8 }) {
  const st = data.report || {};
  const cert = st.certification || {};
  return (
    <>
      <Sec n={start} title="Professional Legal Lens" testId="legal-s8">{LENS.map(([k, t]) => st[k] && <div key={k}><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{t}</p><p className="whitespace-pre-wrap">{st[k]}</p></div>)}</Sec>
      <Sec n={start + 1} title="Options and Resources" testId="legal-s9"><Bullets label="Identified for professional consideration" items={[...(st.options_resources || []), ...(st.options_custom || [])]} empty="None selected." /></Sec>
      <Sec n={start + 2} title="Possible Conflict-Resolution Path" testId="legal-s10"><Bullets label="Selected paths" items={st.conflict_resolution_paths} empty="Not yet selected." />{st.conflict_resolution_explanation && <p><span className="text-xs font-bold uppercase tracking-widest text-muted-foreground block">Professional explanation</span>{st.conflict_resolution_explanation}</p>}</Sec>
      {data.safety_notice_text && <Sec n={start + 3} title="Safety Considerations" testId="legal-s11"><p className="italic">{data.safety_notice_text}</p></Sec>}
      <Sec n={data.safety_notice_text ? start + 4 : start + 3} title="Professional Statement" testId="legal-s12">
        <p className="rounded-md bg-secondary/50 p-3 text-xs italic flex gap-2"><Lock className="h-4 w-4 shrink-0" /> {data.certification_text}</p>
        {st.professional_certified ? <dl className="grid gap-2 sm:grid-cols-3" data-testid="legal-certified">{[["Certified by", st.professional_certified_name], ["Date", st.professional_certified_date], ["Title", cert.title], ["Bar number", cert.bar_number], ["Firm / organization", cert.organization], ["Version", st.legal_version]].filter(([, v]) => v).map(([k, v]) => <div key={k}><dt className="text-xs text-muted-foreground">{k}</dt><dd className="font-medium">{v}</dd></div>)}</dl>
          : <p className="text-xs font-semibold text-amber-800" data-testid="legal-not-certified">NOT YET CERTIFIED — DRAFT</p>}
      </Sec>
      {!data.is_sample ? null : <p className="text-xs text-center text-muted-foreground">Fictional sample. <Link to="/samples" className="underline">All sample reports</Link></p>}
    </>
  );
}
