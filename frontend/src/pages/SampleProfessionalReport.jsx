import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, Gavel, Lock } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

const Sec = ({ n, title, children, testId }) => (
  <section className="bg-white border border-border rounded-lg p-6" data-testid={testId}>
    <h2 className="text-lg font-semibold flex items-center gap-2"><span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{n}</span>{title}</h2>
    <div className="mt-3 space-y-3 text-sm leading-relaxed">{children}</div>
  </section>
);
const Field = ({ label, text }) => text ? <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</p><p className="whitespace-pre-wrap">{text}</p></div> : null;
const Bullets = ({ label, items }) => items?.length > 0 && <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</p><ul className="mt-1 space-y-1">{items.map((x, i) => <li key={i} className="pl-4 relative before:absolute before:left-0 before:content-['•']">{x}</li>)}</ul></div>;

export default function SampleProfessionalReport() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/joint/sample-professional-report").then((r) => setD(r.data)).catch(() => {}); }, []);
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/joint/sample-professional-report/pdf`;
  if (!d) return <div className="min-h-screen bg-background" data-testid="sample-pro-report-loading" />;
  const st = d.statement, fw = st.framework, f = d.findings;
  return (
    <div className="min-h-screen bg-background" data-testid="sample-pro-report-page">
      <header className="bg-white border-b border-border"><div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between gap-3">
        <Link to="/samples" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="sample-pro-back"><ArrowLeft className="h-4 w-4" /> Sample Reports</Link>
        <BrandLogo size="text-xl" />
        <Button size="sm" asChild data-testid="sample-pro-pdf-btn"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> Download Sample PDF</a></Button>
      </div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-5">
        <div className="rounded-lg border-2 border-brand-purple/30 bg-brand-purple/5 p-6">
          <p className="text-xs font-bold uppercase tracking-widest text-brand-purple flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Legal · Professional &amp; Court only</p>
          <h1 className="text-3xl sm:text-4xl font-extrabold mt-1" data-testid="sample-pro-title">Sample Professional Report</h1>
          <p className="text-sm text-muted-foreground mt-2" data-testid="sample-pro-note">Fictional case, fictional professional, fictional court. This is the single legal deliverable a professional submits to the court: the parents' Joint Report findings are infused into it, and options, resources and conflict-management techniques appear <strong>only</strong> here — never in the parents' report. It contains no custody recommendation, credibility finding or determination of "which parent is right."</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-4 text-sm">
            <div><p className="text-xs text-muted-foreground">Court</p><p className="font-semibold">{d.court.court_name}</p></div>
            <div><p className="text-xs text-muted-foreground">Cause No.</p><p className="font-semibold">{d.court.cause_number}</p></div>
            <div><p className="text-xs text-muted-foreground">Align case</p><p className="font-mono font-semibold">{d.case_code}</p></div>
            <div><p className="text-xs text-muted-foreground">Professional</p><p className="font-semibold">{d.professional.name} · {d.professional.pro_role}</p></div>
          </div>
        </div>
        <Sec n={1} title="Case & Referral" testId="sample-pro-s1"><Field label="Role and basis of involvement" text={st.role_basis} /></Sec>
        <Sec n={2} title="Materials Reviewed" testId="sample-pro-s2"><p>{st.materials_reviewed.join(" · ")}</p></Sec>
        <Sec n={3} title="Process Completed by the Parents" testId="sample-pro-s3"><p>{st.process_summary}</p></Sec>
        <Sec n={4} title="Joint Assessment Findings" testId="sample-pro-s4">
          <p className="text-xs italic text-muted-foreground">Infused from the Joint Alignment Report ({f.subject_label}). Differences are listed by area only; neither parent's individual responses appear.</p>
          <Bullets label="Areas of alignment" items={f.alignment} /><Bullets label="Differences in perspective" items={f.differences} /><Bullets label="Child-focused considerations" items={f.child_focused} />
        </Sec>
        <Sec n={5} title="Co-Parenting Ability Level" testId="sample-pro-s5">
          <p className="inline-block rounded-full px-3 py-1 text-xs font-semibold text-white" style={{ background: fw.color }} data-testid="sample-pro-level">Level {fw.score}/10 — {fw.label}</p>
          <p><strong>{fw.framework_title}.</strong> {fw.framework}</p>
          <p className="text-xs italic text-muted-foreground">Suggested from the Joint Report: Level {d.suggested_score?.score} — {d.suggested_score?.rationale}</p>
          <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Ability Level across submitted versions</p>
            <ol className="mt-1 flex flex-wrap items-center gap-2 text-xs" data-testid="sample-pro-history">{d.level_history.map((h, i) => <li key={h.version} className="flex items-center gap-2"><span className="inline-flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold text-white" style={{ background: h.color }}>{h.score}</span><span>v{h.version} · {h.at}{h.superseded ? " · superseded" : ""}{h.note && <span className="block italic text-muted-foreground">From Level {h.changed_from}: {h.note}</span>}</span>{i < d.level_history.length - 1 && <span>→</span>}</li>)}</ol></div>
        </Sec>
        <Sec n={6} title="Parent Alignment — Based on Joint Report" testId="sample-pro-s6">
          <Field label="Where the parents agree / are aligned" text={st.alignment_areas} /><Field label="Where the parents do not agree / are not aligned" text={st.further_attention} />
          <Field label="Partial alignment / potential areas for agreement" text={st.partial_alignment} /><Field label="Professional alignment summary" text={st.alignment_summary} />
        </Sec>
        <Sec n={7} title="Conflict Management — Approaches to Conflict" testId="sample-pro-s7">
          <Bullets label="Options & resources" items={[...fw.subject_options, ...fw.resources, ...fw.tools]} /><Bullets label="Conflict-management techniques" items={fw.techniques} />
          <Field label="Resources / interventions considered" text={st.resources_considered} />
        </Sec>
        <Sec n={8} title="Roadmap" testId="sample-pro-s8"><Field label="Current status" text={st.current_status} /><Field label="Recommended next steps for facilitation" text={st.next_steps} /></Sec>
        <Sec n={9} title="Professional Summary" testId="sample-pro-s9">
          <Field label="Professional observations" text={st.observations} />
          <p className="rounded-md bg-secondary/50 p-3 text-xs italic flex gap-2"><Lock className="h-4 w-4 shrink-0" /> {d.attestation_text}</p>
        </Sec>
        <div className="bg-white border border-border rounded-lg p-6 text-center" data-testid="sample-pro-cta">
          <p className="font-semibold text-lg">Ready to prepare a real Professional Report?</p>
          <p className="text-sm text-muted-foreground mt-1">Create a professional account, open a case, and the report builds itself from the parents' Joint Report.</p>
          <Link to="/auth?mode=register" className="inline-block mt-4"><Button data-testid="sample-pro-register-btn">Create a Free Professional Account</Button></Link>
        </div>
      </main>
    </div>
  );
}
