import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, Eye, Gavel, Lock, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { SampleEmailForm } from "@/components/SampleEmailForm";
import { SampleLensTour, StartTourButton, useSampleLensTour } from "@/components/SampleLensTour";

const Sec = ({ n, title, children, testId }) => (
  <section className="bg-white border border-border rounded-lg p-6" data-testid={testId}>
    <h2 className="text-lg font-semibold flex items-center gap-2"><span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{n}</span>{title}</h2>
    <div className="mt-3 space-y-3 text-sm leading-relaxed">{children}</div>
  </section>
);
const Field = ({ label, text }) => text ? <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</p><p className="whitespace-pre-wrap">{text}</p></div> : null;
const Bullets = ({ label, items }) => items?.length > 0 && <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</p><ul className="mt-1 space-y-1">{items.map((x, i) => <li key={i} className="pl-4 relative before:absolute before:left-0 before:content-['•']">{x}</li>)}</ul></div>;
const KV = ({ rows }) => <dl className="grid gap-2 sm:grid-cols-2">{rows.map(([k, v]) => v && <div key={k}><dt className="text-xs text-muted-foreground">{k}</dt><dd className="font-semibold">{v}</dd></div>)}</dl>;
const Rating = ({ label, score, cls, testId }) => cls && (
  <div className="rounded-md border border-brand-purple/30 bg-brand-purple/5 p-3" data-testid={testId}>
    <p className="font-semibold">{label}: <span className="text-brand-purple">{score}/10 — {cls.label}</span>{cls.mode && <span className="text-muted-foreground"> · {cls.mode}</span>}</p>
    <p className="text-xs text-muted-foreground mt-1">Typical strengths at this level: {cls.strengths.join("; ")}. Typical gaps: {cls.gaps.join("; ")}.</p>
  </div>
);
const Provider = ({ p }) => p?.name && <p className="text-xs"><strong>Provider:</strong> {p.name} — {p.specialty} · {p.contact}</p>;

const ParentSec = ({ n, role, rep, cls }) => {
  const name = rep[`parent_${role}_name`];
  return (
    <Sec n={n} title={`Individual Assessment — ${name}`} testId={`sample-lens-s${n}`}>
      <Rating label={`${name} co-parenting ability`} score={rep[`parent_${role}_rating`]} cls={cls} testId={`sample-lens-rating-${role}`} />
      <Field label={`Where ${name} does well`} text={rep[`parent_${role}_strengths`]} /><Field label={`Where ${name} struggles`} text={rep[`parent_${role}_gaps`]} />
      <Field label="Professional notes" text={rep[`parent_${role}_notes`]} />
      <Bullets label={`${name} — individual resources`} items={rep[`parent_${role}_resources`]} /><Provider p={rep[`parent_${role}_provider`]} />
    </Sec>
  );
};

export default function SampleLegalLensReport() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/joint/sample-legal-lens").then((r) => setD(r.data)).catch(() => {}); }, []);
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/joint/sample-legal-lens/pdf`;
  const tour = useSampleLensTour(!!d);
  if (!d) return <div className="min-h-screen bg-background" data-testid="sample-lens-loading" />;
  const rep = d.report, cls = d.classification;
  return (
    <div className="min-h-screen bg-background" data-testid="sample-lens-page">
      <header className="bg-white border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2">
        <Link to="/samples" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground shrink-0" data-testid="sample-lens-back"><ArrowLeft className="h-4 w-4" /> <span className="hidden sm:inline">Sample Reports</span><span className="sm:hidden">Back</span></Link>
        <div className="hidden sm:block"><BrandLogo size="text-xl" /></div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" asChild data-testid="sample-lens-viewpdf-btn"><a href={`${pdf}?inline=1`} target="_blank" rel="noopener noreferrer"><Eye className="h-4 w-4 mr-1" /> <span className="hidden sm:inline">View PDF</span><span className="sm:hidden">PDF</span></a></Button>
          <Button size="sm" asChild data-testid="sample-lens-pdf-btn"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> <span className="hidden sm:inline">Download PDF</span><span className="sm:hidden">Save</span></a></Button>
        </div>
      </div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-5">
        {tour.open && <SampleLensTour onDone={tour.close} />}
        <div className="flex justify-end gap-2"><StartTourButton onClick={tour.start} /><SampleEmailForm endpoint="/joint/sample-legal-lens/email" label="Sample Legal Lens Report" idPrefix="sample-lens-page" /></div>
        <div className="rounded-lg border-2 border-brand-purple/30 bg-brand-purple/5 p-6">
          <p className="text-xs font-bold uppercase tracking-widest text-brand-purple flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Legal · Professional &amp; Court only</p>
          <h1 className="text-3xl sm:text-4xl font-extrabold mt-1" data-testid="sample-lens-title">Sample Professional Report — Legal Lens Review and Report to Court</h1>
          <p className="text-sm text-muted-foreground mt-2" data-testid="sample-lens-note">A fully completed, <strong>fictional</strong> example of the professional legal report as it reads when finalized. Parents never see this report. It contains no custody recommendation, credibility finding, diagnosis or legal conclusion.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-4 text-sm">
            <div><p className="text-xs text-muted-foreground">Court</p><p className="font-semibold">{rep.court_county}</p></div>
            <div><p className="text-xs text-muted-foreground">Cause No.</p><p className="font-semibold">{rep.cause_number}</p></div>
            <div><p className="text-xs text-muted-foreground">Align case</p><p className="font-mono font-semibold">{d.case.case_code}</p></div>
            <div><p className="text-xs text-muted-foreground">Status</p><p className="font-semibold capitalize" data-testid="sample-lens-status">{rep.status.replace(/_/g, " ")}</p></div>
          </div>
        </div>
        <Sec n={1} title="Case Information" testId="sample-lens-s1">
          <KV rows={[["Case / Matter", rep.matter_name], ["Professional", `${rep.professional_name} · ${rep.professional_role}`], ["Parent A", rep.parent_a_name], ["Parent B", rep.parent_b_name], ["Report date", rep.report_date], ["Child / subject", `${d.case.child_name} · ${d.case.subject_label}`]]} />
        </Sec>
        <Sec n={2} title="Safety First — Receipt of Individual Family Violence Assessment(s)" testId="sample-lens-s2">
          <KV rows={[["Parent A FV assessment", rep.fv_a_received], ["Parent B FV assessment", rep.fv_b_received], ["Joint process appropriate?", rep.joint_process_appropriate]]} />
          <Field label="Safety notes / safeguards" text={rep.safety_notes} />
          <p className="text-xs italic text-muted-foreground flex gap-2"><ShieldCheck className="h-4 w-4 shrink-0" /> {d.notes.safety}</p>
        </Sec>
        <ParentSec n={3} role="a" rep={rep} cls={cls.parent_a} /><ParentSec n={4} role="b" rep={rep} cls={cls.parent_b} />
        <Sec n={5} title="Joint Co-Parenting Assessment" testId="sample-lens-s5">
          <Rating label="Joint co-parenting ability" score={rep.joint_rating} cls={cls.joint} testId="sample-lens-rating-joint" />
          <Field label="Where the parents do well together" text={rep.joint_strengths} /><Field label="Where the parents struggle together" text={rep.joint_gaps} /><Field label="Professional joint assessment notes" text={rep.joint_notes} />
        </Sec>
        <Sec n={6} title="Joint Resources" testId="sample-lens-s6"><Bullets label="Selected joint resources" items={rep.joint_resources} /><Provider p={rep.joint_provider} /></Sec>
        <Sec n={7} title="Parent Alignment — Based on Joint Report" testId="sample-lens-s7">
          <Field label="Where the parents agree / are aligned" text={rep.alignment_agreements} /><Field label="Where the parents do not agree / are not aligned" text={rep.alignment_disagreements} />
          <Field label="Partial alignment / potential areas for agreement" text={rep.partial_alignment} /><Field label="Professional alignment summary" text={rep.alignment_summary} />
        </Sec>
        <Sec n={8} title="Conflict Management — Approaches to Conflict" testId="sample-lens-s8">
          <Bullets label="Selected approaches" items={rep.conflict_management_options} />
          <Bullets label={`Automatic guidance for joint rating ${rep.joint_rating} — consider`} items={cls.joint?.guidance} />
          <Field label="Conflict management rationale / recommended structure" text={rep.conflict_management_rationale} />
          <p className="text-xs italic text-muted-foreground">{d.notes.rating}</p>
        </Sec>
        <Sec n={9} title="Roadmap" testId="sample-lens-s9"><Field label="Short-term goals — next 30 to 90 days" text={rep.short_term_goals} /><Field label="Long-term goals — 6 to 12 months" text={rep.long_term_goals} /></Sec>
        <Sec n={10} title="Professional Legal Lens Review and Report to Court" testId="sample-lens-s10">
          <Field label="Professional summary" text={rep.professional_summary} />
          <KV rows={[["Next review / reassessment", rep.next_review_date], ["Professional signature", rep.signature_name], ["Title", rep.professional_title], ["Date finalized", rep.finalized_at?.slice(0, 10)]]} />
          <p className="rounded-md bg-secondary/50 p-3 text-xs italic flex gap-2"><Lock className="h-4 w-4 shrink-0" /> {d.notes.tagline}</p>
        </Sec>
        <div className="bg-white border border-border rounded-lg p-6 text-center" data-testid="sample-lens-cta">
          <p className="font-semibold text-lg">Ready to prepare a real Legal Lens Report?</p>
          <p className="text-sm text-muted-foreground mt-1">Create a professional account, open a case, and the report prefills from the parents' assessments and Joint Report.</p>
          <Link to="/auth?mode=register" className="inline-block mt-4"><Button data-testid="sample-lens-register-btn">Create a Free Professional Account</Button></Link>
        </div>
      </main>
    </div>
  );
}
