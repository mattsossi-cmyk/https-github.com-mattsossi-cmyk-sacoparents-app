import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, Eye, Gavel, Lock, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { SampleEmailForm } from "@/components/SampleEmailForm";
import { SampleLensTour, StartTourButton, useSampleLensTour } from "@/components/SampleLensTour";
import { ScaleTable, PathwayList } from "@/components/LensScale";

const Sec = ({ n, title, children, testId }) => (
  <section className="bg-white border border-border rounded-lg p-6" data-testid={testId}>
    <h2 className="text-lg font-semibold flex items-center gap-2 border-b border-border pb-2 text-brand-purple">{n !== undefined && <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{n}</span>}{title}</h2>
    <div className="mt-3 space-y-3 text-sm leading-relaxed">{children}</div>
  </section>
);
const H3 = ({ children }) => <h3 className="font-semibold text-align-green">{children}</h3>;
const Lines = ({ label, text, ordered }) => { const items = (text || "").split("\n").filter(Boolean); const Tag = ordered ? "ol" : "ul"; return items.length > 0 && <div>{label && <p className="font-semibold">{label}</p>}<Tag className={`${ordered ? "list-decimal" : "list-disc"} pl-5 space-y-1`}>{items.map((x, i) => { const [t, ...rest] = x.split(": "); return <li key={i}>{rest.length ? <><strong>{t}:</strong> {rest.join(": ")}</> : x}</li>; })}</Tag></div>; };
const KV = ({ rows }) => <dl className="grid gap-2 sm:grid-cols-3">{rows.map(([k, v]) => v && <div key={k}><dt className="text-xs text-muted-foreground">{k}</dt><dd className="font-semibold">{v}</dd></div>)}</dl>;

const ParentBlock = ({ role, rep, testId }) => (
  <div data-testid={testId}>
    <H3>{rep[`parent_${role}_name`]} (Rated: Level {rep[`parent_${role}_rating`]})</H3>
    <ul className="list-disc pl-5 space-y-1 mt-1">
      <li><strong>What's Working Well (Strengths):</strong> {rep[`parent_${role}_strengths`]}</li>
      <li><strong>Real-World Example (Gaps):</strong> {rep[`parent_${role}_gaps`]}</li>
      <li><strong>Key Growth Areas:</strong><Lines text={rep[`parent_${role}_growth`]} ordered /></li>
    </ul>
  </div>
);

export default function SampleLegalLensReport() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/joint/sample-legal-lens").then((r) => setD(r.data)).catch(() => {}); }, []);
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/joint/sample-legal-lens/pdf`;
  const tour = useSampleLensTour(!!d);
  if (!d) return <div className="min-h-screen bg-background" data-testid="sample-lens-loading" />;
  const rep = d.report, cls = d.classification, lib = d.library, risk = rep.risk_screening || {};
  return (
    <div className="min-h-screen bg-background" data-testid="sample-lens-page">
      <header className="bg-white border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2">
        <Link to="/samples" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground shrink-0" data-testid="sample-lens-back"><ArrowLeft className="h-4 w-4" /> <span className="hidden sm:inline">Sample Reports</span><span className="sm:hidden">Back</span></Link>
        <div className="hidden sm:block"><BrandLogo size="text-xl" /></div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" asChild data-testid="sample-lens-viewpdf-btn"><a href={`${pdf}?inline=1`} target="_blank" rel="noopener noreferrer"><Eye className="h-4 w-4 mr-1" /> <span className="hidden sm:inline">View PDF</span><span className="sm:hidden">PDF</span></a></Button>
          <Button size="sm" asChild data-testid="sample-lens-pdf-btn"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> <span className="hidden sm:inline">Print / Save as PDF</span><span className="sm:hidden">Save</span></a></Button>
        </div>
      </div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-5">
        {tour.open && <SampleLensTour onDone={tour.close} />}
        <div className="flex justify-end gap-2"><StartTourButton onClick={tour.start} /><SampleEmailForm endpoint="/joint/sample-legal-lens/email" label="Sample Professional Report" idPrefix="sample-lens-page" /></div>
        <div className="rounded-lg border-2 border-brand-purple/30 bg-white p-6 border-b-4">
          <p className="text-xs font-bold uppercase tracking-widest text-brand-purple flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Legal · Professional &amp; Court only · Sample (fictional data)</p>
          <h1 className="text-3xl sm:text-4xl font-extrabold mt-1 text-brand-purple" data-testid="sample-lens-title">SA CoParents Align Professional Evaluation Report</h1>
          <p className="text-sm text-muted-foreground mt-3" data-testid="sample-lens-note"><strong className="text-foreground">Platform:</strong> sacoparentsalign.com<br /><strong className="text-foreground">Focus:</strong> Comprehensive 1–10 Scale Analysis (Joint &amp; Individual Behaviors), Stage-Specific Profiles, Resources &amp; Actionable Roadmap</p>
          <div className="mt-4"><KV rows={[["Court", rep.court_county], ["Cause No.", rep.cause_number], ["Align case", d.case.case_code], ["Professional", `${rep.professional_name} · ${rep.professional_role}`], ["Report date", rep.report_date], ["Status", rep.status.replace(/_/g, " ")]]} /></div>
        </div>
        <Sec title="What This Report Covers" testId="sample-lens-intro"><p>{d.notes.intro}</p></Sec>
        <Sec n={1} title="Safety First: Checking for Domestic Violence & IPV Risks" testId="sample-lens-s1">
          <p>Before evaluating co-parenting scores or suggesting joint meetings, we screen for <strong>Intimate Partner Violence (IPV) and coercive control</strong>.</p>
          <p className="rounded-r-md border-l-4 border-amber-500 bg-amber-50 p-3 text-xs">{d.notes.alert}</p>
          <KV rows={[["Parent A FV assessment", rep.fv_a_received], ["Parent B FV assessment", rep.fv_b_received], ["Joint process appropriate?", rep.joint_process_appropriate]]} />
          <H3>Risk Screening Summary</H3>
          <ul className="list-disc pl-5 space-y-1" data-testid="sample-lens-risk">{lib.risk_categories.map(([k, label]) => <li key={k}><strong>{label}:</strong> <strong>{risk[k]?.level}.</strong> {risk[k]?.note}</li>)}</ul>
          <p><strong>Takeaway:</strong> {rep.safety_takeaway}</p>
          <p className="text-xs italic text-muted-foreground flex gap-2"><ShieldCheck className="h-4 w-4 shrink-0" /> {d.notes.safety}</p>
        </Sec>
        <Sec n={2} title="Detailed Individual Breakdown for Parent A & Parent B" testId="sample-lens-s2">
          <ParentBlock role="a" rep={rep} testId="sample-lens-parent-a" /><ParentBlock role="b" rep={rep} testId="sample-lens-parent-b" />
          <div data-testid="sample-lens-joint"><H3>Joint Dynamic Summary (Rated: Level {rep.joint_rating})</H3>
            <p className="mt-1"><strong>Operating Dynamic:</strong> <strong>{cls.joint.mode} Mode</strong> — {cls.joint.label}.<br /><strong>Summary:</strong> {rep.joint_notes}</p></div>
        </Sec>
        <Sec n={3} title="Comprehensive 1–10 Co-Parenting Scale: Joint & Individual Behaviors" testId="sample-lens-s3"><ScaleTable scale={lib.scale_table} cls={cls} rep={rep} /></Sec>
        <Sec n={4} title="Post-Rating Roadmap: Short-Term & Long-Term Goals" testId="sample-lens-s4">
          <H3>A. Short-Term Goals (Next 30 to 90 Days)</H3><Lines text={rep.short_term_goals} />
          <H3>B. Long-Term Goals (6 to 12 Months)</H3><Lines text={rep.long_term_goals} />
        </Sec>
        <Sec n={5} title="Resource & Support Options" testId="sample-lens-s5">
          <div className="overflow-x-auto"><table className="w-full border-collapse text-xs" data-testid="sample-lens-resources">
            <thead><tr className="bg-brand-purple/10 text-brand-purple">{["Category", "Recommended Resource / Specialist", "Service Focus & Scope"].map((h) => <th key={h} className="border border-border p-2 text-left">{h}</th>)}</tr></thead>
            <tbody>{rep.resource_rows.map((r, i) => <tr key={i} className={i % 2 ? "bg-secondary/40" : ""}><td className="border border-border p-2 font-bold">{r.category}</td><td className="border border-border p-2 font-semibold">{r.resource}</td><td className="border border-border p-2">{r.focus}</td></tr>)}</tbody>
          </table></div>
        </Sec>
        <Sec n={6} title="Checking In: Regular Reassessments" testId="sample-lens-s6">
          <p>By checking in <strong>{rep.reassess_interval.replace("Every ", "every ")}</strong> via SA CoParents Align, parents can track progress against their roadmap:</p>
          <ul className="list-disc pl-5 space-y-1"><li>{rep.reassess_up}</li><li>{rep.reassess_down}</li></ul>
          <p className="text-xs text-muted-foreground">Next review / reassessment: {rep.next_review_date}</p>
        </Sec>
        <Sec n={7} title="Conflict Resolution Pathways (Levels 1–10)" testId="sample-lens-s7">
          <PathwayList pathways={lib.pathways} rating={rep.joint_rating} recommended={cls.joint?.pathway?.key} chosen={rep.conflict_pathway} />
          <p><strong>Rationale:</strong> {rep.conflict_management_rationale}</p>
          <p className="text-xs italic text-muted-foreground">{d.notes.rating}</p>
        </Sec>
        <Sec title="Professional Certification" testId="sample-lens-s8">
          <KV rows={[["Professional signature", rep.signature_name], ["Title", rep.professional_title], ["Date finalized", rep.finalized_at?.slice(0, 10)]]} />
          <p className="rounded-md bg-secondary/50 p-3 text-xs italic flex gap-2"><Lock className="h-4 w-4 shrink-0" /> {d.notes.tagline}</p>
        </Sec>
        <div className="bg-white border border-border rounded-lg p-6 text-center" data-testid="sample-lens-cta">
          <p className="font-semibold text-lg">Ready to prepare a real Professional Evaluation Report?</p>
          <p className="text-sm text-muted-foreground mt-1">Create a professional account, open a case, and the report prefills from the parents' assessments and Joint Report.</p>
          <Link to="/auth?mode=register" className="inline-block mt-4"><Button data-testid="sample-lens-register-btn">Create a Free Professional Account</Button></Link>
        </div>
      </main>
    </div>
  );
}
