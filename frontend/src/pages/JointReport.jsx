import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Printer, CheckCircle2, Circle, Share2, ClipboardList } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ReminderPreviewButton } from "@/components/ReminderPreview";
import { AgreementDocument } from "@/components/AgreementDocument";
import { ProWorkspace } from "@/components/ProWorkspace";
import { JointPauseControl } from "@/components/JointPauseControl";
import { FoundationStatements } from "@/components/FoundationStatements";
import { CaseAttachments } from "@/components/FoundationAttachments";
import { ShareFoundation } from "@/components/ShareFoundation";
import { SafetyScreeningPanel } from "@/components/SafetyScreeningPanel";
import { InviteCadenceSettings } from "@/components/InviteCadenceSettings";
const NO_REPORT = new Set(["agreement", "foundation"]);
import { CompareView } from "@/components/CompareView";
import { SampleWalkthrough } from "@/components/SampleWalkthrough";

function Section({ num, title, children, testId }) {
  return (
    <div className="mb-10" data-testid={testId}>
      <h2 className="text-2xl font-semibold mb-4" data-testid={`${testId}-heading`}>
        <span className="text-accent font-display mr-2">{num}.</span>{title}
      </h2>
      {children}
    </div>
  );
}

export default function JointReport() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [report, setReport] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [shareEmail, setShareEmail] = useState("");
  const [error, setError] = useState(null);
  const [view, setView] = useState("compare");

  const toggleRedact = async (role, key, redacted) => {
    try {
      await api.put(`/joint/reports/${id}/redactions`, { role, key, redacted });
      const rr = await api.get(`/joint/reports/${id}/report`);
      setReport(rr.data);
      toast.success(redacted ? "Passage redacted for release" : "Passage restored");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const load = () => {
    api.get(`/joint/reports/${id}`)
      .then((r) => {
        setDetail(r.data);
        if (r.data.status === "ready") {
          api.get(`/joint/reports/${id}/report`).then((rr) => setReport(rr.data)).catch((e) => setError(formatApiError(e)));
        }
      })
      .catch((e) => setError(formatApiError(e)));
  };

  useEffect(() => {
    load();
    api.get("/joint/config").then((r) => setSubjects(r.data.subjects)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const cancel = async () => {
    try {
      await api.post(`/joint/invitations/${detail.invitation.id}/cancel`);
      toast.success("Invitation cancelled");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const changeSubject = async (subject) => {
    try {
      await api.patch(`/joint/invitations/${detail.invitation.id}`, { subject });
      toast.success("Subject updated");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const share = async () => {
    try {
      const { data } = await api.post(`/joint/reports/${id}/share`, { email: shareEmail });
      toast.success(`Shared with ${data.shared_with}`);
      setShareEmail("");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6" data-testid="joint-error">
        <div className="max-w-md text-center">
          <p className="text-lg font-medium">{error}</p>
          <Link to="/dashboard" className="inline-block mt-6"><Button variant="outline" data-testid="joint-error-back-btn">Back to dashboard</Button></Link>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" data-testid="joint-loading">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </div>
    );
  }

  const ready = detail.status === "ready";
  const rows = detail.my_role
    ? [["Your assessment", detail.participants[detail.my_role]], ["Other parent's assessment", detail.participants[detail.my_role === "a" ? "b" : "a"]]]
    : [[`${detail.participants.a.name || "Parent A"}'s assessment`, detail.participants.a], [`${detail.participants.b.name || "Parent B"}'s assessment`, detail.participants.b]];

  return (
    <div className="min-h-screen bg-background" data-testid="joint-report-page">
      <header className="no-print bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="joint-back-link">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <BrandLogo size="text-xl" />
          {ready && report && detail.kind !== "foundation" && (
            <Button size="sm" className="gap-2" asChild data-testid="joint-print-btn">
              <a href={`${process.env.REACT_APP_BACKEND_URL}/api/joint/reports/${id}/pdf`} download aria-label="Download PDF">
                <Printer className="h-4 w-4" /> <span className="hidden sm:inline">Download PDF</span>
              </a>
            </Button>
          )}
          {ready && report && detail.is_creator && !NO_REPORT.has(detail.kind) && (
            <Button size="sm" variant="outline" className="gap-2 ml-2" asChild data-testid="session-prep-btn">
              <a href={`${process.env.REACT_APP_BACKEND_URL}/api/joint/reports/${id}/session-prep.pdf`} download aria-label="Download Session Prep Sheet">
                <ClipboardList className="h-4 w-4" /> <span className="hidden sm:inline">Session Prep Sheet</span>
              </a>
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <div className="no-print bg-white border border-border rounded-lg p-6 mb-8" data-testid="joint-status-card">
          <p className="text-xs uppercase tracking-widest text-accent font-semibold">{detail.subject_label}</p>
          <h1 className="text-2xl font-semibold mt-1" data-testid="joint-status-title">{detail.child_name ? `${detail.child_name} — Joint Report` : "Joint Report"}</h1>
          {detail.case_code && <p className="mt-1 text-xs text-muted-foreground" data-testid="joint-case-code">Alignment Case: <span className="font-semibold tracking-widest">{detail.case_code}</span></p>}
          {detail.case_reference && <p className="mt-1 text-xs text-muted-foreground" data-testid="joint-case-ref">Your case reference: {detail.case_reference} (private to you)</p>}
          <div className="mt-4 space-y-2 text-sm">
            {rows.map(([label, p]) => (
              <div key={label} className="flex items-center gap-2" data-testid={`status-row-${label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
                {p.completed ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                <span>{label}: {p.completed ? (p.imported ? "Complete (imported from sacoparentsapp.online)" : "Complete") : p.accepted ? "In progress" : "Invitation sent"}</span>
              </div>
            ))}
            <div className="flex items-center gap-2" data-testid="status-row-report">
              {ready ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
              <span className={ready ? "font-semibold" : ""}>Joint Report: {ready ? "Ready" : "Waiting for both parents"}</span>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2 items-center">
            {detail.my_role && !detail.participants[detail.my_role].completed && detail.participants[detail.my_role].accepted && (
              <Link to={detail.kind === "foundation" ? "/foundation" : `/joint/${id}/assess`}><Button size="sm" data-testid="status-complete-btn">{detail.kind === "foundation" ? "Write My Foundation Statement" : "Complete My Assessment"}</Button></Link>
            )}
            {detail.is_creator && detail.invitation && detail.invitation.status === "pending" && (
              <>
                <ReminderPreviewButton iid={detail.invitation.id} label="Resend Invitation" testId="status-resend-btn" />
                <select className="h-9 rounded-md border border-input bg-white px-2 text-sm" value={detail.subject} onChange={(e) => changeSubject(e.target.value)} data-testid="status-change-subject">
                  {subjects.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
                <Button size="sm" variant="ghost" className="text-destructive" onClick={cancel} data-testid="status-cancel-btn">Cancel Invitation</Button>
              </>
            )}
          </div>
          {detail.is_creator && detail.invitation && detail.invitation.status === "pending" && (
            <p className="mt-3 text-xs text-muted-foreground" data-testid="status-invitation-code">
              Invitation code for {detail.invitation.invitee_email}: <span className="font-semibold tracking-widest">{detail.invitation.code}</span>
            </p>
          )}
          {detail.kind !== "foundation" && <SafetyScreeningPanel rid={id} />}
          {!detail.my_role && detail.kind !== "foundation" && <InviteCadenceSettings rid={id} />}
          {detail.my_role && !detail.is_creator && <ShareFoundation rid={id} shared={detail.my_foundation_shared} onShared={() => setDetail((d) => ({ ...d, my_foundation_shared: true }))} />}
          {ready && detail.my_role && (
            <div className="mt-5 pt-4 border-t border-border">
              <p className="text-sm font-medium mb-2">Share with a professional (mediator, attorney, therapist):</p>
              <div className="flex gap-2 max-w-md">
                <Input type="email" value={shareEmail} onChange={(e) => setShareEmail(e.target.value)} placeholder="professional@example.com" className="h-10" data-testid="share-email-input" />
                <Button size="sm" variant="outline" className="gap-1.5 h-10" onClick={share} disabled={!shareEmail.trim()} data-testid="share-professional-btn">
                  <Share2 className="h-3.5 w-3.5" /> Email to professional
                </Button>
              </div>
            </div>
          )}
        </div>

        {ready && report && detail.kind === "agreement" && <AgreementDocument report={report} />}

        {ready && report && !NO_REPORT.has(detail.kind) && detail.is_creator && (
          <SampleWalkthrough active={!!detail.is_demo} onStart={() => setView("report")} />
        )}

        {ready && report && !NO_REPORT.has(detail.kind) && detail.is_creator && (
          <div className="no-print flex gap-2 mb-4" role="tablist" data-testid="report-view-tabs">
            {[["compare", "Compare"], ["report", "Joint Report"]].map(([k, label]) => (
              <button key={k} type="button" role="tab" aria-selected={view === k} onClick={() => setView(k)} className={`text-sm font-medium rounded-full px-4 py-2 border transition-colors ${view === k ? "bg-primary text-white border-primary" : "bg-white border-border hover:border-primary/50"}`} data-testid={`view-tab-${k}`}>{label}</button>
            ))}
          </div>
        )}

        {ready && report && !NO_REPORT.has(detail.kind) && detail.is_creator && view === "compare" && (
          <CompareView report={report} onOpenReport={() => setView("report")} />
        )}

        {ready && report && !NO_REPORT.has(detail.kind) && (!detail.is_creator || view === "report") && (
          <div className="report-paper rounded-lg p-8 sm:p-12" data-testid="joint-report-document">
            <div className="text-center border-b border-border pb-8 mb-10">
              <BrandLogo size="text-xl" />
              <h1 className={`text-4xl font-extrabold mt-4 ${report.is_safety ? "text-red-700" : "text-brand-purple"}`} data-testid="joint-report-title">{report.report_title}</h1>
              <div className="mt-4 text-sm text-muted-foreground space-y-1">
                <p data-testid="joint-report-child">Child: <strong className="text-foreground">{report.child_name}</strong></p>
                <p data-testid="joint-report-subject">Subject: <strong className="text-foreground">{report.subject_label}</strong></p>
                <p data-testid="joint-report-participants">Participants: {report.parent_a_name} / {report.parent_b_name}</p>
                <p data-testid="joint-report-date">{report.date}</p>
              </div>
            </div>

            {report.is_safety && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8" data-testid="jr-safety-notice">
                <p className="text-sm text-red-800 font-medium">{report.confidentiality_note}</p>
              </div>
            )}

            <Section num={1} title="Purpose of This Report" testId="jr-purpose">
              <p className="text-muted-foreground leading-relaxed">{report.purpose}</p>
            </Section>

            <Section num={2} title="What Both Parents Agree About" testId="jr-alignment">
              <p className="text-sm font-semibold text-align-green mb-3">Strong Alignment — both parents indicated that:</p>
              <ul className="space-y-2" data-testid="jr-alignment-list">
                {report.alignment_statements.map((s, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm" data-testid={`jr-alignment-item-${i}`}>
                    <CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" /> {s}
                  </li>
                ))}
              </ul>
            </Section>

            <Section num={3} title="Where the Parents See Things Differently" testId="jr-differences">
              {report.differences.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No significant differences in perspective were identified.</p>
              ) : (
                <div className="space-y-5">
                  {report.differences.map((d, i) => (
                    <div key={i} className="border border-border rounded-lg p-5" data-testid={`jr-difference-${i}`}>
                      <p className="font-semibold mb-3">{d.area}</p>
                      <div className="grid sm:grid-cols-2 gap-4">
                        <div className="bg-muted/40 rounded-md p-4">
                          <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-2">{report.parent_a_name}'s Perspective</p>
                          <p className={`text-sm leading-relaxed ${d.redacted?.a ? "italic text-muted-foreground" : ""}`}>{d.parent_a}</p>
                          {detail.is_creator && d.key && <button type="button" onClick={() => toggleRedact("a", d.key, !d.redacted?.a)} className="mt-2 text-xs font-semibold text-brand-purple underline-offset-2 hover:underline" data-testid={`jr-redact-a-${d.key}`}>{d.redacted?.a ? "Restore" : "Redact before release"}</button>}
                        </div>
                        <div className="bg-muted/40 rounded-md p-4">
                          <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-2">{report.parent_b_name}'s Perspective</p>
                          <p className={`text-sm leading-relaxed ${d.redacted?.b ? "italic text-muted-foreground" : ""}`}>{d.parent_b}</p>
                          {detail.is_creator && d.key && <button type="button" onClick={() => toggleRedact("b", d.key, !d.redacted?.b)} className="mt-2 text-xs font-semibold text-brand-purple underline-offset-2 hover:underline" data-testid={`jr-redact-b-${d.key}`}>{d.redacted?.b ? "Restore" : "Redact before release"}</button>}
                        </div>
                      </div>
                      <p className="mt-3 text-sm italic text-muted-foreground">{d.reframe}</p>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section num={4} title="Child's Identified Needs" testId="jr-needs">
              <p className="text-sm text-muted-foreground mb-3">Based upon both parents' responses, the report identifies several possible shared needs:</p>
              <ul className="grid sm:grid-cols-2 gap-2" data-testid="jr-needs-list">
                {report.child_needs.map((n) => (
                  <li key={n} className="flex items-center gap-2 text-sm bg-muted/40 rounded-md px-4 py-3">
                    <CheckCircle2 className="h-4 w-4 text-primary shrink-0" /> {n}
                  </li>
                ))}
              </ul>
            </Section>

            <Section num={5} title="Alignment Map" testId="jr-map">
              <table className="w-full text-sm border border-border rounded-lg overflow-hidden" data-testid="jr-map-table">
                <thead>
                  <tr className="bg-brand-purple/10 text-left text-brand-purple">
                    <th className="px-4 py-3 font-semibold">Subject</th>
                    <th className="px-4 py-3 font-semibold">Alignment</th>
                  </tr>
                </thead>
                <tbody>
                  {report.alignment_map.map((row, i) => (
                    <tr key={i} className="border-t border-border" data-testid={`jr-map-row-${i}`}>
                      <td className="px-4 py-3 font-medium">{row.area}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-2 ${row.status === "Strong alignment" ? "text-align-green" : row.status === "Moderate alignment" ? "text-align-yellow" : "text-align-blue"}`}>
                          <span className={`h-2.5 w-2.5 rounded-full ${row.status === "Strong alignment" ? "bg-align-green" : row.status === "Moderate alignment" ? "bg-align-yellow" : "bg-align-blue"}`} />
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>

            <Section num={6} title="Areas for Conversation" testId="jr-conversation">
              <ul className="space-y-2" data-testid="jr-conversation-list">
                {report.conversation.map((q, i) => (
                  <li key={i} className="flex gap-3 text-sm" data-testid={`jr-conversation-item-${i}`}>
                    <span className="text-accent font-semibold">•</span> {q}
                  </li>
                ))}
              </ul>
            </Section>

            <Section num={7} title="Potential Areas of Alignment" testId="jr-paragraph">
              <div className="bg-secondary/50 border-l-4 border-accent rounded-r-lg p-5">
                <p className="font-display text-lg italic leading-relaxed">{report.alignment_paragraph}</p>
              </div>
            </Section>

            <Section num={8} title="Questions for the Parents" testId="jr-questions">
              <ul className="space-y-2" data-testid="jr-questions-list">
                {report.questions.map((q, i) => (
                  <li key={i} className="border-l-4 border-align-blue rounded-r-lg bg-muted/40 p-4 font-display text-lg italic" data-testid={`jr-question-${i}`}>{q}</li>
                ))}
              </ul>
            </Section>

            <Section num={9} title="Possible Next Steps" testId="jr-next-steps">
              <div className="grid sm:grid-cols-2 gap-3" data-testid="jr-next-steps-list">
                {report.next_steps.map((s, i) => (
                  <div key={i} className="border border-border rounded-md px-4 py-3 text-sm font-medium" data-testid={`jr-next-step-${i}`}>{s}</div>
                ))}
              </div>
            </Section>

            <div className="text-center border-t border-border pt-10">
              <h3 className="font-display text-4xl sm:text-5xl font-bold text-align-purple" data-testid="jr-philosophy-heading">{report.philosophy_heading}</h3>
              <p className="mt-3 text-muted-foreground max-w-xl mx-auto">{report.philosophy_note}</p>
              <p className="mt-6 text-sm italic text-muted-foreground max-w-xl mx-auto" data-testid="jr-philosophy-line">"{report.philosophy}"</p>
            </div>
          </div>
        )}
        {detail.is_creator && <FoundationStatements rid={id} items={detail.foundation_statements} safetyRoute={detail.safety_route} safetyCaseId={detail.safety_case_id} />}
        {detail.is_creator && <CaseAttachments rid={id} />}
        {detail.joint_blocked && <div className="mb-6 rounded-lg border border-border bg-secondary/40 p-4 text-sm" role="status" data-testid="joint-blocked-notice">{detail.joint_blocked_message}</div>}
        {detail.is_creator && <JointPauseControl rid={id} paused={detail.joint_paused} onChange={(p) => setDetail((d) => ({ ...d, joint_paused: p }))} />}
        {report?.redaction_notice && <p className="mb-4 text-xs text-muted-foreground" data-testid="jr-redaction-notice">{report.redaction_notice}</p>}
        {detail.is_creator && <ProWorkspace rid={id} steps={ready && report && !NO_REPORT.has(detail.kind) ? [...(report.next_steps || []), ...(report.options || [])] : null} outcome={detail.session_outcome} onOutcomeSaved={(o) => setDetail((d) => ({ ...d, session_outcome: o }))} courtReady={!!(ready && report && !NO_REPORT.has(detail.kind))} />}
      </main>
    </div>
  );
}
