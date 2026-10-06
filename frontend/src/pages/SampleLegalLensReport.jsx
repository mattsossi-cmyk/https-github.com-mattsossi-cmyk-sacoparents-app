import { useEffect, useState } from "react";
import { SixQuestions, SourceLegend, StatementDivider } from "@/components/ReportFraming";
import { ReportCover } from "@/components/ReportCover";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, Eye, Gavel, Lock, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { SampleEmailForm } from "@/components/SampleEmailForm";
import { ListenButton } from "@/components/ListenButton";
import { SampleLensTour, StartTourButton, useSampleLensTour } from "@/components/SampleLensTour";
import { IndividualScaleTable, JointScaleTable, growthOf } from "@/components/LensScale";
import { ReportPrinciple, ChildFocusSummary, PathwayPicker, ReportHeader, ReportDisclaimer, AlignmentStatusGrid, LensSec } from "@/components/LensSections";

const Sec = ({ n, title, children, testId }) => <LensSec n={n} title={title} testId={testId}>{children}</LensSec>;
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
        <div className="flex justify-end gap-2"><ListenButton text={`Sample Professional Alignment Report. ${d.notes?.intro || ""} Professional statement: ${rep.professional_summary || ""} Court summary: ${rep.court_summary_text || ""}`} testId="sample-lens-listen" /><StartTourButton onClick={tour.start} /><SampleEmailForm endpoint="/joint/sample-legal-lens/email" label="Sample Professional Report" idPrefix="sample-lens-page" /></div>
        <ReportHeader right={<span className="rounded-full bg-white/15 px-3 py-1 text-xs font-semibold" data-testid="sample-lens-note">Sample · fictional data</span>} />
        <ReportCover pro={d.professional} testId="sample-lens-cover" />
        <details className="rounded-lg border border-border bg-white p-3" data-testid="sample-lens-preview-image"><summary className="cursor-pointer text-sm font-semibold text-brand-purple">See the printed report layout (11 numbered sections)</summary><img src="/alignment-report-preview.jpg" alt="Printed Professional Alignment Report — 11-section layout preview" className="mt-3 w-full rounded-md border border-border" loading="lazy" /></details>
        <div className="rounded-lg border border-border bg-white p-4"><KV rows={[["Court", rep.court_county], ["Cause No.", rep.cause_number], ["Align case", d.case.case_code], ["Professional", `${rep.professional_name} · ${rep.professional_role}`], ["Report date", rep.report_date], ["Status", rep.status.replace(/_/g, " ")]]} /></div>
        <SixQuestions testId="sample-lens-six-questions" />
        <SourceLegend testId="sample-lens-source-legend" />
        <Sec n={1} title="Case & Assessment Overview" testId="sample-lens-s1">
          <p data-testid="sample-lens-intro">{d.notes.intro}</p>
          <H3>Assessments completed</H3>
          <ul className="list-disc pl-5 space-y-1" data-testid="sample-lens-assessments">{d.readiness.map((r) => <li key={r.key}>{r.label}: <strong>{r.done ? "Complete" : r.na ? "N/A" : "Not received"}</strong></li>)}</ul>
          <p><strong>Sources of information considered:</strong> {rep.sources_considered}</p>
        </Sec>
        <Sec n={2} title="Alignment Snapshot & Safety Screening" testId="sample-lens-s2">
          <AlignmentStatusGrid rep={rep} />
          <H3>Safety screening (IPV &amp; coercive control)</H3>
          <p className="rounded-r-md border-l-4 border-amber-500 bg-amber-50 p-3 text-xs">{d.notes.alert}</p>
          <KV rows={[["Parent A FV assessment", rep.fv_a_received], ["Parent B FV assessment", rep.fv_b_received], ["Joint process appropriate?", rep.joint_process_appropriate]]} />
          <ul className="list-disc pl-5 space-y-1" data-testid="sample-lens-risk">{lib.risk_categories.map(([k, label]) => <li key={k}><strong>{label}:</strong> <strong>{risk[k]?.level}.</strong> {risk[k]?.note}</li>)}</ul>
          <p><strong>Takeaway:</strong> {rep.safety_takeaway}</p>
          <p className="text-xs italic text-muted-foreground flex gap-2"><ShieldCheck className="h-4 w-4 shrink-0" /> {d.notes.safety}</p>
        </Sec>
        <Sec n={3} title={`Parent A Perspective — ${rep.parent_a_name}`} testId="sample-lens-s3">
          <p className="text-xs italic text-muted-foreground">Each parent is presented separately and neutrally (PARENT-REPORTED INFORMATION summarized by the professional); no determination is made about which account is correct.</p>
          <ParentBlock role="a" rep={rep} testId="sample-lens-parent-a" />
          <IndividualScaleTable scale={lib.scale_table} row={cls.parent_a?.row} rating={rep.parent_a_rating} role="a" name={rep.parent_a_name} growth={growthOf(rep, "a")} />
        </Sec>
        <Sec n={4} title={`Parent B Perspective — ${rep.parent_b_name}`} testId="sample-lens-s4b">
          <ParentBlock role="b" rep={rep} testId="sample-lens-parent-b" />
          <IndividualScaleTable scale={lib.scale_table} row={cls.parent_b?.row} rating={rep.parent_b_rating} role="b" name={rep.parent_b_name} growth={growthOf(rep, "b")} />
        </Sec>
        <Sec n={5} title="Joint Co-Parenting Assessment" testId="sample-lens-joint">
          <p><strong>Joint rating:</strong> Level {rep.joint_rating} — <strong>{cls.joint.mode} Mode</strong> — {cls.joint.label}</p>
          <Lines label="Areas of alignment" text={rep.alignment_agreements || rep.joint_strengths} />
          <Lines label="Areas of partial alignment" text={rep.partial_alignment} />
          <Lines label="Areas of differing perspectives" text={rep.alignment_disagreements || rep.joint_gaps} />
          <p><strong>Shared concerns:</strong> {rep.shared_concerns}</p>
          <p><strong>Issues requiring further discussion or professional attention:</strong> {rep.joint_notes}</p>
          <JointScaleTable scale={lib.scale_table} row={cls.joint?.row} rating={rep.joint_rating} />
        </Sec>
        <Sec n={6} title="Child-Focused Legal Issues" testId="sample-lens-s4"><ChildFocusSummary categories={lib.child_focus_categories} value={rep.child_focus} testId="sample-lens-child-focus" /></Sec>
        <Sec n={7} title="Options & Resources" testId="sample-lens-s5">
          <div className="overflow-x-auto"><table className="w-full border-collapse text-xs" data-testid="sample-lens-resources">
            <thead><tr className="bg-brand-blue/10 text-brand-blue">{["Category", "Recommended Resource / Specialist", "Service Focus & Scope"].map((h) => <th key={h} className="border border-border p-2 text-left">{h}</th>)}</tr></thead>
            <tbody>{rep.resource_rows.map((r, i) => <tr key={i} className={i % 2 ? "bg-secondary/40" : ""}><td className="border border-border p-2 font-bold">{r.category}</td><td className="border border-border p-2 font-semibold">{r.resource}</td><td className="border border-border p-2">{r.focus}</td></tr>)}</tbody>
          </table></div>
          <aside className="mt-3 rounded-md border border-teal-300 bg-[#e8f7f7] p-4 text-sm" data-testid="sample-lens-research-base">
            <p className="text-xs font-bold uppercase tracking-widest text-teal-700">Research Base · Perplexity web research (fictional sample)</p>
            <p className="mt-1 leading-relaxed">{rep.research_base?.text}</p>
            <ol className="mt-2 list-decimal pl-5 text-xs">{(rep.research_base?.citations || []).map((c) => <li key={c.index} className="break-all text-brand-purple">{c.url}</li>)}</ol>
            <p className="mt-2 text-[11px] text-muted-foreground">In a real report this footer is fetched live for the issues and pathways you select, near your registered ZIP code, and appears under Section 7 in the PDF. Professional-reviewed; never a finding or recommendation.</p>
          </aside>
        </Sec>
        <Sec n={8} title="Conflict Resolution Pathways" testId="sample-lens-s7">
          <PathwayPicker lib={{ ...lib, notes: d.notes }} rep={rep} cls={cls} set={() => {}} readOnly />
          <p><strong>Why these pathways are relevant:</strong> {rep.pathway_rationale}</p>
          <p className="text-xs italic text-muted-foreground">{d.notes.rating}</p>
        </Sec>
        <StatementDivider testId="sample-lens-statement-divider" />
        <Sec n={9} title="Legal Conflict & Agreement-Building Analysis" testId="sample-lens-s9-legal">
          <div className="grid gap-3 sm:grid-cols-2">
            <Lines label="Areas potentially capable of agreement" text={rep.agreement_building_opportunities || rep.alignment_agreements} />
            <Lines label="Issues requiring further resolution" text={rep.issues_requiring_attention || rep.alignment_disagreements} />
            <Lines label="Existing agreements / orders noted" text={rep.existing_agreements} />
            <Lines label="Procedural considerations" text={rep.procedural_considerations} />
          </div>
        </Sec>
        <Sec n={10} title="Professional Legal Statement & Roadmap" testId="sample-lens-s8">
          <p className="text-xs italic text-muted-foreground">The professional's own observations, interpretation, recommendations and conclusions — distinct from parent-reported information and system- or AI-generated summaries.</p>
          <p data-testid="sample-lens-statement">{rep.professional_summary}</p>
          <H3>30–90 Day Goals</H3><Lines text={rep.short_term_goals} />
          <H3>How We Will Know Things Are Improving</H3><div data-testid="sample-lens-success-indicators"><Lines text={rep.success_indicators} /></div>
          <H3>Long-Term Goals (6 to 12 Months)</H3><Lines text={rep.long_term_goals} />
          <p>Reassessment <strong>{rep.reassess_interval.replace("Every ", "every ")}</strong> · next review {rep.next_review_date}</p>
          <ul className="list-disc pl-5 space-y-1"><li>{rep.reassess_up}</li><li>{rep.reassess_down}</li></ul>
          <ReportPrinciple notes={d.notes} testId="sample-lens-principle" />
        </Sec>
        <Sec n={11} title="Concise Court Summary" testId="sample-lens-s9">
          <p data-testid="sample-lens-court-summary">{rep.court_summary_text}</p>
          <H3>Professional Certification</H3>
          <KV rows={[["Professional signature", rep.signature_name], ["Title", rep.professional_title], ["Date finalized", rep.finalized_at?.slice(0, 10)]]} />
          <ReportDisclaimer notes={d.notes} signature={rep.signature_name} date={rep.finalized_at?.slice(0, 10)} />
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
