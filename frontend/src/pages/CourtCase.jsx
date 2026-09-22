import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Circle, Download, Gavel } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { CourtStatusSummary } from "@/components/CourtStatusSummary";
import { CourtThread } from "@/components/CourtThread";
import { HearingDate } from "@/components/CourtCaseCard";
import { CourtLegalSummary } from "@/components/CourtLegalSummary";

const Section = ({ n, title, children, testId }) => (
  <section className="rounded-lg border border-border bg-white p-6" data-testid={testId}>
    <h2 className="text-lg font-semibold flex items-center gap-2"><span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{n}</span>{title}</h2>
    <div className="mt-4">{children}</div>
  </section>
);

const Stat = ({ label, value, testId }) => (
  <div className="rounded-md bg-secondary/50 px-4 py-3" data-testid={testId}><p className="text-2xl font-bold text-brand-purple">{value ?? "—"}</p><p className="text-xs text-muted-foreground">{label}</p></div>
);

const List = ({ title, items, empty }) => (
  <div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{title}</p>
    {items.length === 0 ? <p className="mt-1 text-sm italic text-muted-foreground">{empty}</p> : <ul className="mt-1 space-y-1 text-sm">{items.map((t, i) => <li key={i} className="pl-4 relative before:absolute before:left-0 before:content-['•']">{typeof t === "string" ? t : t.text || t.label || JSON.stringify(t)}</li>)}</ul>}
  </div>
);

const STMT_ALL = [["role_basis", "Role and basis of involvement"], ["process_summary", "Process completed"], ["alignment_areas", "Where the parents agree / are aligned"], ["further_attention", "Where the parents do not agree / are not aligned"],
  ["partial_alignment", "Partial alignment / potential areas for agreement"], ["alignment_summary", "Professional alignment summary"],
  ["resources_considered", "Resources / Interventions Considered"], ["current_status", "Current Status"], ["observations", "Professional Observations"], ["safety_considerations", "Safety considerations"], ["next_steps", "Recommended next steps"]];
const ALIGNMENT_KEYS = ["alignment_areas", "further_attention", "partial_alignment", "alignment_summary"];

export default function CourtCase({ sample = false }) {
  const { refId } = useParams();
  const { user, logout } = useAuth();
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const load = () => api.get(sample ? "/court-dashboard/sample-case" : `/court-dashboard/cases/${refId}`).then((r) => setD(r.data)).catch((e) => setErr(e?.response?.data?.detail || "Not found"));
  useEffect(() => { load(); }, [refId, sample]);
  const ref = d?.referral;
  const pdf = (pid) => (sample ? `${process.env.REACT_APP_BACKEND_URL}/api/joint/sample-legal-lens/pdf?inline=1` : `${process.env.REACT_APP_BACKEND_URL}/api/court-dashboard/packets/${pid}/pdf`);
  return (
    <div className="min-h-screen bg-background" data-testid={sample ? "court-sample-page" : "court-case-page"}>
      <header className="border-b border-border bg-white"><div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between gap-3"><BrandLogo size="text-xl" /><div className="flex items-center gap-3 text-sm"><span className="text-xs font-bold uppercase tracking-widest text-brand-purple hidden sm:inline">Judicial Portal{sample ? " · Sample" : ""}</span>{sample ? <Button size="sm" asChild data-testid="court-sample-register-btn"><Link to="/auth?court=1">Court sign-in / register</Link></Button> : <><span className="text-muted-foreground hidden sm:inline">{user?.name}</span><Button size="sm" variant="ghost" onClick={logout} data-testid="court-logout-btn">Sign out</Button></>}</div></div></header>
      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {sample ? (
          <div className="rounded-lg border-2 border-accent/40 bg-accent/5 p-4 text-sm" data-testid="court-sample-banner">
            <p className="font-semibold">Read-only sample — fictional case, professional and court.</p>
            <p className="text-muted-foreground mt-1">This is exactly what a judge sees after a professional's authorized submission. Judges never see raw parent responses, private journals or draft material, and no custody, credibility or legal determination is made. <Link to="/samples" className="text-brand-purple underline" data-testid="court-sample-back">Back to Sample Reports</Link></p>
          </div>
        ) : <Link to="/court-dashboard" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground" data-testid="court-case-back"><ArrowLeft className="h-4 w-4" /> Court-referred cases</Link>}
        {err && <p className="text-red-700" data-testid="court-case-error">{err}</p>}
        {d && ref && (
          <>
            <div className="rounded-lg border border-border bg-white p-6" data-testid="court-case-header">
              <p className="text-xs uppercase tracking-widest text-accent font-semibold flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Court-referred case</p>
              <h1 className="text-3xl font-semibold mt-1">Cause No. {ref.cause_number}{ref.child_initials ? ` · Child ${ref.child_initials}` : ""}</h1>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5 text-sm">
                <div><p className="text-xs text-muted-foreground">SA CoParents Case ID</p><p className="font-mono font-semibold" data-testid="court-case-id">{d.case_code || "—"}</p></div>
                <div><p className="text-xs text-muted-foreground">Court Referral Status</p><p className="font-semibold" data-testid="court-case-status">{d.stage?.label}</p></div>
                <div><p className="text-xs text-muted-foreground">Assigned Professional</p><p className="font-semibold" data-testid="court-case-pro">{ref.professional_name}</p></div>
                <div><p className="text-xs text-muted-foreground">Parents Invited</p><p className="font-semibold">{d.parents_invited}</p></div>
                <div><p className="text-xs text-muted-foreground">Parents Participating</p><p className="font-semibold" data-testid="court-case-participating">{d.parents_participating}</p></div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><span className="text-xs text-muted-foreground">Hearing date:</span>{sample ? <span className="font-semibold" data-testid="court-sample-hearing">{ref.hearing_date}</span> : <HearingDate x={ref} onSaved={(hd) => setD((x) => ({ ...x, referral: { ...x.referral, hearing_date: hd } }))} />}{ref.overdue && <span className="text-xs font-bold text-red-700" data-testid="court-case-overdue">Within 7 days — nothing submitted</span>}</div>
            </div>

            <Section n={1} title="Case Status" testId="court-case-checklist">
              <ul className="grid gap-2 sm:grid-cols-2">{d.checklist.map((c) => <li key={c.label} className={`flex items-center gap-2 text-sm ${c.done ? "" : "text-muted-foreground"}`}>{c.done ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4" />}{c.label}</li>)}</ul>
            </Section>

            <Section n={2} title="AI Court Summary" testId="court-case-ai">
              <CourtStatusSummary referralId={ref.id} summary={d.status_summary} readOnly={sample} onRefreshed={(s) => setD((x) => ({ ...x, status_summary: s }))} />
              <div className="mt-4 grid grid-cols-3 gap-3">
                <Stat label="Alignment Areas" value={d.counts?.alignment_areas} testId="court-stat-alignment" />
                <Stat label="Discussion Areas" value={d.counts?.discussion_areas} testId="court-stat-discussion" />
                <Stat label="Assessment Completion" value={d.counts ? `${d.counts.completion_pct}%` : "0%"} testId="court-stat-completion" />
              </div>
              <p className="mt-3 text-xs text-muted-foreground" data-testid="court-case-disclaimer">No determination of credibility, parenting fitness, or legal conclusions is made by SA CoParents.</p>
            </Section>

            <Section n={3} title="Joint Assessment Report" testId="court-case-reports">
              {d.reports.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="court-case-no-reports">No Joint Report has been submitted to the court yet. Reports appear here only after the professional's authorized submission.</p> : d.reports.map((r) => (
                <div key={r.key} className="space-y-4" data-testid={`court-report-${r.key}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold">{r.label} <span className="text-xs text-muted-foreground">· v{r.version} · {r.case_code}</span></p><Button size="sm" variant="outline" asChild data-testid="court-report-pdf"><a href={pdf(r.packet_id)} download><Download className="h-4 w-4 mr-1" /> Submitted packet PDF</a></Button></div>
                  <List title="Areas of Alignment" items={r.alignment} empty="None identified." />
                  <List title="Areas of Difference" items={r.differences} empty="None identified." />
                  <List title="Child-Focused Considerations" items={r.child_focused} empty="—" />
                </div>
              ))}
            </Section>

            <Section n={4} title="Professional Report" testId="court-case-statement">
              {!d.statement ? <p className="text-sm text-muted-foreground" data-testid="court-case-no-statement">Not yet submitted.</p> : (
                <div className="space-y-3 text-sm">
                  <p><span className="text-muted-foreground">Professional:</span> <strong>{d.statement.professional_name}</strong>{d.statement.role && <> · <span className="text-muted-foreground">Role:</span> {d.statement.role}</>} · submitted {d.statement.submitted_at?.slice(0, 10)}</p>
                  {d.statement.materials_reviewed?.length > 0 && <p data-testid="court-statement-materials"><span className="text-muted-foreground">Materials reviewed:</span> {d.statement.materials_reviewed.join(" · ")}</p>}
                  {d.statement.legal_report_included && (
                    <div className="rounded-md border-2 border-brand-purple/30 bg-brand-purple/5 p-3 flex flex-wrap items-center justify-between gap-2" data-testid="court-legal-report">
                      <p><span className="rounded-full bg-brand-purple/10 px-2 py-0.5 text-[10px] font-bold tracking-widest text-brand-purple mr-2">EVALUATION REPORT</span><strong>Professional Evaluation Report</strong> v{d.statement.legal_version} — certified, attached to this frozen submission{d.statement.legal_sha256 && <code className="ml-2 text-[11px] text-muted-foreground">SHA-256 {d.statement.legal_sha256.slice(0, 16)}…</code>}</p>
                      {!sample && <Button size="sm" variant="outline" asChild data-testid="court-legal-report-pdf"><a href={`${process.env.REACT_APP_BACKEND_URL}/api/court-dashboard/packets/${d.statement.packet_id}/legal-report.pdf`} download><Download className="h-4 w-4 mr-1" /> Evaluation Report PDF</a></Button>}
                    </div>
                  )}
                  <CourtLegalSummary s={d.statement.legal_summary} />

                  {STMT_ALL.filter(([k]) => d.statement[k] && !(d.statement.legal_summary && ALIGNMENT_KEYS.includes(k))).map(([k, t]) => <div key={k}><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{t}</p><p className="leading-relaxed whitespace-pre-wrap">{d.statement[k]}</p></div>)}
                  {d.statement.framework && (
                    <div className="rounded-lg border border-border p-4" data-testid="court-statement-framework">
                      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Co-Parenting Ability Level</p>
                      <p className="mt-1 inline-block rounded-full px-3 py-1 text-xs font-semibold text-white" style={{ background: d.statement.framework.color }} data-testid="court-ability-level">Level {d.statement.framework.score}/10 — {d.statement.framework.label}</p>
                      <p className="mt-2"><strong>{d.statement.framework.framework_title}.</strong> {d.statement.framework.framework}</p>
                      {[["subject_options", "Options for the assessed subject"], ["resources", "Resources"], ["tools", "Tools & platforms"], ["techniques", "Conflict-management techniques"]].map(([k, t]) => d.statement.framework[k]?.length > 0 && (
                        <div key={k} className="mt-2"><p className="text-xs font-semibold">{t}</p><ul className="list-disc pl-5 text-xs">{d.statement.framework[k].map((i) => <li key={i}>{i}</li>)}</ul></div>
                      ))}
                    </div>
                  )}
                  {d.level_history?.filter((h) => h.score).length > 0 && (
                    <div className="rounded-lg border border-border p-4" data-testid="court-level-history">
                      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Ability Level across submitted versions</p>
                      <ol className="mt-2 flex flex-wrap items-center gap-2">
                        {d.level_history.filter((h) => h.score).map((h, i, arr) => (
                          <li key={h.version} className="flex items-center gap-2 text-xs" data-testid={`court-level-history-${h.version}`}>
                            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white" style={{ background: h.color }}>{h.score}</span>
                            <span><span className="font-semibold">v{h.version}</span> · {h.at?.slice(0, 10)}{h.superseded ? " · superseded" : ""}{h.changed_from && h.note && <span className="block max-w-xs text-[11px] italic text-muted-foreground" data-testid={`court-level-note-${h.version}`}>From Level {h.changed_from}: {h.note}</span>}{h.growth && <span className="block text-[11px] text-align-green font-semibold" data-testid={`court-level-growth-${h.version}`}>Growth areas met: A {h.growth.a.met}/{h.growth.a.total} · B {h.growth.b.met}/{h.growth.b.total}</span>}</span>
                            {i < arr.length - 1 && <span className="text-muted-foreground">→</span>}
                          </li>
                        ))}
                      </ol>
                      <p className="mt-2 text-[11px] text-muted-foreground">Level changes reflect the professional's assessment of the co-parenting dynamic over time; they are not findings about either parent.</p>
                    </div>
                  )}
                </div>
              )}
              {d.submissions.length > 0 && <ul className="mt-4 space-y-1 text-xs text-muted-foreground" data-testid="court-case-submissions">{d.submissions.map((s) => <li key={s.version}>Version {s.version} · {s.at?.slice(0, 16).replace("T", " ")} · SHA-256 {s.sha256?.slice(0, 16)}…{s.superseded ? " · superseded" : ""}</li>)}</ul>}
            </Section>

            <Section n={5} title="Court–Professional Communication" testId="court-case-thread">
              {sample ? <p className="text-sm text-muted-foreground" data-testid="court-sample-thread-note">In a live case this is a case-specific, timestamped message thread between the court and the assigned professional, with an AI-neutral summary of open requests. Disabled in the sample.</p> : <CourtThread baseUrl={`/court-dashboard/cases/${ref.id}`} side="court" />}
            </Section>
          </>
        )}
      </main>
    </div>
  );
}
