import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Copy, Check, Mail } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ConfidentialityNotice } from "@/components/ConfidentialityNotice";
import { InvitationPreviewButton } from "@/components/InvitationPreview";

const PRO_ASSESSMENTS = [
  { key: "co_parenting", label: "Co-Parenting", hint: "Shared parenting priorities and routines" },
  { key: "communication", label: "Communication", hint: "How parents exchange information" },
  { key: "education", label: "Educational", hint: "School, homework and learning needs" },
  { key: "medical", label: "Medical", hint: "Health care, appointments and decisions" },
  { key: "psychological", label: "Psychological", hint: "Emotional wellbeing and support" },
  { key: "foundation", label: "Foundation Statement", hint: "Each parent writes a Child-Focused Foundation Statement" },
  { key: "complete", label: "Complete Alignment", hint: "All five core areas in one assessment", multi: ["co_parenting", "communication", "education", "medical", "psychological"] },
];


export default function JointNew() {
  const [subjects, setSubjects] = useState([]);
  const [connections, setConnections] = useState([]);
  const [step, setStep] = useState(0);
  const [subject, setSubject] = useState(null);
  const [customSubject, setCustomSubject] = useState("");
  const [childName, setChildName] = useState("");
  const [coName, setCoName] = useState("");
  const [coEmail, setCoEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(null);
  const [copied, setCopied] = useState(false);
  const [multiSubjects, setMultiSubjects] = useState([]);
  const [paName, setPaName] = useState("");
  const [paEmail, setPaEmail] = useState("");
  const [mediatorEmail, setMediatorEmail] = useState("");
  const [caseRef, setCaseRef] = useState("");
  const [referral, setReferral] = useState(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const isPro = user?.role === "professional" || user?.role === "admin";
  const isAgreement = searchParams.get("kind") === "agreement";
  const SAFETY_KEYS = ["safety", "risk", "safety_communication", "safeguards"];
  const activeSubjects = multiSubjects.length > 0 ? multiSubjects : subject ? [subject] : [];
  const isSafety = activeSubjects.length > 0 && activeSubjects.every((k) => SAFETY_KEYS.includes(k));
  const panel = (isPro && !isAgreement ? ["child", "invite", "subject"] : ["subject", "child", "invite"])[step];
  const pickAssessment = (s) => {
    if (s.multi) { setMultiSubjects(s.multi); setSubject(s.multi[0]); }
    else { setMultiSubjects([]); setSubject(s.key); }
  };

  useEffect(() => {
    const kind = searchParams.get("kind");
    if (kind === "agreement") {
      setSubject("co_parenting");
      setStep(1);
      return;
    }
    const single = searchParams.get("subject");
    const multi = searchParams.get("subjects");
    const pro = user?.role === "professional" || user?.role === "admin";
    if (multi) {
      const keys = multi.split(",").filter(Boolean);
      setMultiSubjects(keys);
      setSubject(keys[0]);
      if (!pro) setStep(1);
    } else if (single) {
      setSubject(single);
      if (!pro) setStep(1);
    }
  }, [searchParams, user]);

  useEffect(() => {
    api.get("/joint/config").then((r) => setSubjects(r.data.subjects)).catch((e) => toast.error(formatApiError(e)));
    api.get("/joint/connections").then((r) => setConnections(r.data)).catch(() => {});
    const refId = searchParams.get("referral");
    if (refId) {
      api.get(`/professional/court-referrals/${refId}`).then((r) => {
        const x = r.data;
        setReferral(x);
        const first = (x.requested_reports || []).find((r) => r.subjects.length > 0);
        if (first && first.subjects.length > 1) { setMultiSubjects(first.subjects); setSubject(first.subjects[0]); }
        else if (first) setSubject(first.subjects[0]);
        else if (x.subject) setSubject(x.subject);
        if (x.parent_a_name) setPaName(x.parent_a_name);
        if (x.parent_a_email) setPaEmail(x.parent_a_email);
        if (x.parent_b_name) setCoName(x.parent_b_name);
        if (x.parent_b_email) setCoEmail(x.parent_b_email);
        if (x.child_initials) setChildName(x.child_initials);
        setCaseRef(`Cause No. ${x.cause_number}`);
      }).catch((e) => toast.error(formatApiError(e)));
    }
  }, [searchParams]);

  const pickConnection = (email) => {
    const c = connections.find((x) => x.other_email === email);
    if (c) {
      setCoName(c.other_name);
      setCoEmail(c.other_email);
      if (c.child_name && !childName) setChildName(c.child_name);
    }
  };

  const submit = async () => {
    setBusy(true);
    try {
      const base = { child_name: childName };
      if (multiSubjects.length > 1) {
        base.subject = multiSubjects[0];
        base.subjects = multiSubjects;
      } else {
        base.subject = subject;
        base.custom_subject = customSubject;
      }
      const url = isAgreement ? "/joint/agreements" : "/joint/reports/professional";
      const body = isAgreement
        ? { child_name: childName, parent_a_name: paName, parent_a_email: paEmail, parent_b_name: coName, parent_b_email: coEmail }
        : { ...base, parent_a_name: paName, parent_a_email: paEmail, parent_b_name: coName, parent_b_email: coEmail, case_reference: caseRef, court_referral_id: referral?.id || "" };
      const { data } = await api.post(url, body);
      toast.success("Invitations sent — private share links are ready below");
      setCreated(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy — copy it manually");
    }
  };

  return (
    <div className="min-h-screen bg-background" data-testid="joint-new-page">
      <header className="bg-white border-b border-border no-print">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="joint-back-link">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        {referral && (
          <div className="mb-6 rounded-lg border border-brand-purple/30 bg-brand-purple/5 px-4 py-3 text-sm" data-testid="referral-banner">
            <span className="font-semibold text-brand-purple">Court referral</span> · Cause No. {referral.cause_number} · {referral.court_name || "court"} · {referral.judge_name}. Parties pre-filled where the court provided them; the Joint Report and your Professional Statement return to this court.
            {(referral.requested_reports || []).length > 0 && (
              <p className="mt-2" data-testid="referral-requested-reports">
                <span className="font-semibold">Court requests:</span> {referral.requested_reports.map((r) => r.label).join(" · ")}.
                {referral.requested_reports.length > 1 && " The first is pre-selected below; create the remaining reports from the case afterwards."}
                {referral.requested_reports.some((r) => r.key === "agreement") && <> Co-Parenting Agreement: <Link to={`/joint/new?kind=agreement`} className="text-primary underline" data-testid="referral-agreement-link">create it here</Link> after the joint report.</>}
              </p>
            )}
          </div>
        )}
        {created && created.invitations ? (
          <div className="bg-white border border-border rounded-lg p-8" data-testid="pro-invitations-card">
            <div className="text-center mb-8">
              <Mail className="h-10 w-10 text-primary mx-auto mb-4" />
              <h1 className="text-3xl font-semibold">Parent Links Ready</h1>
              {created.case_code && (
                <p className="mt-3 text-sm" data-testid="pro-case-code">Alignment Case: <span className="font-display text-xl font-bold tracking-[0.2em] text-brand-purple">{created.case_code}</span></p>
              )}
              <p className="text-xs text-muted-foreground mt-1" data-testid="pro-case-status">Status: Waiting for both parents</p>
              <p className="text-muted-foreground mt-3 max-w-lg mx-auto">
                Share each parent's private link to collect their information for <strong>{created.subject_label}</strong>
                regarding <strong>{created.child_name || "the child"}</strong>. Each link is unique to that parent —
                their answers stay private and are never shared between parents.
              </p>
            </div>
            {created.invitations.map((inv) => (
              <div key={inv.role} className="bg-muted/50 border border-border rounded-lg p-5 mb-4" data-testid={`pro-share-link-${inv.role}`}>
                <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">
                  Parent {inv.role === "a" ? "A" : "B"} — {inv.invitee_name} ({inv.invitee_email})
                </p>
                <div className="flex items-center gap-2 flex-wrap mt-2">
                  <code className="text-xs bg-white border border-border rounded px-2 py-1.5 flex-1 min-w-0 truncate" data-testid={`pro-link-text-${inv.role}`}>{inv.link}</code>
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => copy(inv.link)} data-testid={`copy-link-${inv.role}-btn`}>
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />} Copy Link
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Backup code: <span className="font-semibold tracking-widest" data-testid={`pro-code-${inv.role}`}>{inv.code}</span> · An email invitation was also sent to {inv.invitee_email}.
                </p>
              </div>
            ))}
            <ConfidentialityNotice variant="professional" />
            <div className="flex justify-center mt-6">
              <Link to="/dashboard" data-testid="pro-done-link">
                <Button variant="outline" data-testid="pro-done-btn">Back to Dashboard</Button>
              </Link>
            </div>
          </div>
        ) : created ? (
          <div className="bg-white border border-border rounded-lg p-8" data-testid="invitation-sent-card">
            <div className="text-center mb-8">
              <Mail className="h-10 w-10 text-primary mx-auto mb-4" />
              <h1 className="text-3xl font-semibold">Invitation Sent</h1>
              <p className="text-muted-foreground mt-3 max-w-lg mx-auto">
                {created.participants.b.name} has been invited to independently provide their perspective
                regarding {created.child_name || "your child"} on the subject of <strong>{created.subject_label}</strong>.
                Their answers remain private until both of you have completed the assessment.
              </p>
            </div>
            <div className="bg-muted/50 border border-border rounded-lg p-5 mb-6">
              <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-2">Alignment Code</p>
              <div className="flex items-center gap-3">
                <span className="font-display text-3xl font-bold tracking-[0.3em]" data-testid="invitation-code-display">{created.invitation.code}</span>
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => copy(created.invitation.code)} data-testid="copy-code-btn">
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />} Copy
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                An email was sent to {created.invitation.invitee_email}. If it doesn't arrive, share this code or the invitation link directly.
              </p>
              <div className="mt-3 flex items-center gap-2">
                <code className="text-xs bg-white border border-border rounded px-2 py-1.5 flex-1 min-w-0 truncate" data-testid="invitation-link-display">{created.invitation.link}</code>
                <Button size="sm" variant="ghost" className="gap-1.5 shrink-0" onClick={() => copy(created.invitation.link)} data-testid="copy-invite-link-btn">
                  <Copy className="h-4 w-4" /> Copy Link
                </Button>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 justify-center">
              <Button className="gap-2" onClick={() => navigate(`/joint/${created.id}/assess`)} data-testid="complete-my-assessment-btn">
                Complete My Assessment <ArrowRight className="h-4 w-4" />
              </Button>
              <Link to="/dashboard" data-testid="back-to-dashboard-link">
                <Button variant="outline" data-testid="back-to-dashboard-btn">Back to Dashboard</Button>
              </Link>
            </div>
          </div>
        ) : (
          <>
            <h1 className="text-4xl font-semibold mb-2" data-testid="joint-new-heading">{isAgreement ? "Create a Co-Parenting Agreement" : isPro ? "Invite Parents" : "Create a Joint Report"}</h1>
            <p className="text-muted-foreground mb-8">{isAgreement ? "Invite the other parent to propose terms for your joint co-parenting agreement. Each parent's proposals stay private until both are complete." : isPro ? "Create the case, enter both parents, choose the assessment, and send two separate secure invitations. Parents never exchange codes — you are the hub." : "One subject. One child. Both parents answer independently — answers stay private until both are complete."}</p>

            <div className="flex items-center gap-2 mb-10" data-testid="joint-steps">
              {(isPro ? ["Create Case", "Invite Parents", "Choose Assessment"] : ["Subject", "Child", "Invite"]).map((s, i) => (
                <div key={s} className="flex items-center gap-2 flex-1 last:flex-none">
                  <span className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold ${i <= step ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`} data-testid={`joint-step-${i}`}>{i + 1}</span>
                  <span className={`text-xs ${i === step ? "font-semibold" : "text-muted-foreground"}`}>{s}</span>
                  {i < 2 && <div className="flex-1 h-px bg-border mx-2" />}
                </div>
              ))}
            </div>

            {panel === "subject" && (
              <div data-testid="joint-step-subject">
                <h2 className="text-2xl font-semibold mb-4">{isPro ? "Choose the assessment" : "What would you like the parents to explore together?"}</h2>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {(isPro ? PRO_ASSESSMENTS.map((a) => ({ ...a, label: a.label })) : subjects).map((s) => (
                    <button
                      key={s.key}
                      onClick={() => pickAssessment(s)}
                      className={`text-left border rounded-lg px-4 py-3 text-sm font-medium transition-colors ${(s.multi ? multiSubjects.length > 1 : subject === s.key && multiSubjects.length <= 1) ? "border-primary bg-secondary/60" : "border-border bg-white hover:bg-muted"}`}
                      data-testid={`subject-${s.key}`}
                    >
                      {s.label}
                      {s.hint && <span className="block text-xs text-muted-foreground font-normal mt-0.5">{s.hint}</span>}
                    </button>
                  ))}
                </div>
                {subject === "custom" && (
                  <div className="mt-4 space-y-2">
                    <Label htmlFor="custom-subject">Custom subject</Label>
                    <Input id="custom-subject" className="h-12" value={customSubject} onChange={(e) => setCustomSubject(e.target.value)} placeholder="e.g. Summer travel plans" data-testid="custom-subject-input" />
                  </div>
                )}
                <div className="mt-8 flex justify-between">
                  {isPro ? <button type="button" onClick={() => setStep(1)} className="text-sm text-muted-foreground hover:text-foreground" data-testid="subject-back-btn">Back</button> : <span />}
                  {isPro ? (
                    <div className="flex items-center gap-2">
                      {!isAgreement && (
                        <InvitationPreviewButton
                          disabled={activeSubjects.length === 0 || busy}
                          sending={busy}
                          onSend={submit}
                          payload={{ child_name: childName, subject: multiSubjects.length > 1 ? multiSubjects[0] : subject, subjects: multiSubjects.length > 1 ? multiSubjects : [], custom_subject: customSubject, parent_a_name: paName, parent_a_email: paEmail, parent_b_name: coName, parent_b_email: coEmail }}
                        />
                      )}
                      <Button onClick={submit} disabled={activeSubjects.length === 0 || busy} className="gap-2 uppercase tracking-wide" data-testid="send-invitation-btn">
                        {busy ? "Sending…" : "Send Invitations"} <Mail className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <Button onClick={() => setStep(1)} disabled={!subject || (subject === "custom" && !customSubject.trim())} className="gap-2" data-testid="subject-next-btn">
                      Continue <ArrowRight className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            )}

            {panel === "child" && (
              <div data-testid="joint-step-child">
                <h2 className="text-2xl font-semibold mb-4">{isPro ? "Create the case" : "Which child is this report about?"}</h2>
                {multiSubjects.length > 1 && subjects.length > 0 && (
                  <p className="text-sm text-muted-foreground mb-4" data-testid="multi-subjects-line">
                    Subjects: {multiSubjects.map((k) => subjects.find((s) => s.key === k)?.label || k).join(" + ")}
                  </p>
                )}
                <div className="bg-white border border-border rounded-lg p-6 space-y-5">
                  {isPro && (
                    <div className="space-y-2">
                      <Label htmlFor="case-ref">Case name / reference (private to you)</Label>
                      <Input id="case-ref" className="h-12" value={caseRef} onChange={(e) => setCaseRef(e.target.value)} placeholder="e.g. Sossi v. — File #2026-114" data-testid="case-reference-input" />
                      <p className="text-xs text-muted-foreground">Never shown to the parents. Align assigns a master Case ID (SA-26-…) and a separate private invitation token for each parent.</p>
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="joint-child">Child's first name or initials</Label>
                    <Input id="joint-child" className="h-12" value={childName} onChange={(e) => setChildName(e.target.value)} placeholder="e.g. Sam" data-testid="joint-child-input" />
                  </div>
                </div>
                <div className="mt-8 flex justify-between">
                  {isPro ? <span /> : <button type="button" onClick={() => setStep(0)} className="text-sm text-muted-foreground hover:text-foreground" data-testid="child-back-btn">Back</button>}
                  <Button onClick={() => setStep(isPro ? 1 : 2)} disabled={!childName.trim()} className="gap-2" data-testid="child-next-btn">
                    Continue <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {panel === "invite" && (
              <div data-testid="joint-step-invite">
                <h2 className="text-2xl font-semibold mb-4">{isPro ? "Invite both parents" : "Invite the other parent"}</h2>
                {isSafety && !isPro && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-5 mb-4" data-testid="safety-pathway-note">
                    <p className="font-semibold text-red-800">Family violence reports are prepared differently.</p>
                    <p className="text-sm text-red-800/80 mt-1 mb-4">
                      This report is created with a third-party mediator — not directly between the parents.
                      Enter your mediator's email. They must have a free SA CoParents professional account.
                    </p>
                    <Label htmlFor="mediator-email" className="text-red-900">Mediator's email</Label>
                    <Input id="mediator-email" type="email" className="h-12 mt-2 bg-white" value={mediatorEmail} onChange={(e) => setMediatorEmail(e.target.value)} placeholder="mediator@example.com" data-testid="mediator-email-input" />
                    <p className="text-xs text-red-800/70 mt-3 font-medium">
                      Confidentiality: your responses will not be shared with the other party. Only the completed comparison is provided to the mediator.
                    </p>
                  </div>
                )}
                {!isPro && connections.length > 0 && (
                  <div className="bg-secondary/50 border border-border rounded-lg p-4 mb-4">
                    <Label className="font-medium">Already connected?</Label>
                    <select className="mt-2 w-full h-12 rounded-md border border-input bg-white px-3 text-sm" defaultValue="" onChange={(e) => pickConnection(e.target.value)} data-testid="connection-select">
                      <option value="" disabled>Select a connected co-parent…</option>
                      {connections.map((c) => (
                        <option key={c.id} value={c.other_email}>{c.other_name} ({c.other_email})</option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="bg-white border border-border rounded-lg p-6 space-y-5">
                  {isPro && (
                    <>
                      <div className="space-y-2">
                        <Label htmlFor="pa-name">Parent 1 first name</Label>
                        <Input id="pa-name" className="h-12" value={paName} onChange={(e) => setPaName(e.target.value)} placeholder="e.g. Ann" data-testid="parent-a-invite-name-input" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="pa-email">Parent 1 email</Label>
                        <Input id="pa-email" type="email" className="h-12" value={paEmail} onChange={(e) => setPaEmail(e.target.value)} placeholder="ann@example.com" data-testid="parent-a-invite-email-input" />
                      </div>
                    </>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="co-name">{isPro ? "Parent 2 first name" : "Co-parent's first name"}</Label>
                    <Input id="co-name" className="h-12" value={coName} onChange={(e) => setCoName(e.target.value)} placeholder="e.g. Jordan" data-testid="co-parent-name-input" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="co-email">{isPro ? "Parent 2 email" : "Co-parent's email"}</Label>
                    <Input id="co-email" type="email" className="h-12" value={coEmail} onChange={(e) => setCoEmail(e.target.value)} placeholder="jordan@example.com" data-testid="co-parent-email-input" />
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid="invite-privacy-note">
                    {isPro ? "Each parent receives their own secure link and completes the assessment privately. Parents never see each other's answers and never exchange codes." : "Each parent keeps a separate login. Your co-parent receives an invitation code — never share your password."}
                  </p>
                </div>
                <div className="mt-6" data-testid="jointnew-confidentiality"><ConfidentialityNotice /></div>
                <div className="mt-8 flex justify-between">
                  <button type="button" onClick={() => setStep(isPro ? 0 : 1)} className="text-sm text-muted-foreground hover:text-foreground" data-testid="invite-back-btn">Back</button>
                  {isPro ? (
                    <Button onClick={() => setStep(2)} disabled={!coName.trim() || !coEmail.trim() || !paName.trim() || !paEmail.trim()} className="gap-2" data-testid="invite-next-btn">
                      Continue <ArrowRight className="h-4 w-4" />
                    </Button>
                  ) : (
                    <Button onClick={submit} disabled={!coName.trim() || !coEmail.trim() || (isSafety && !mediatorEmail.trim()) || busy} className="gap-2" data-testid="send-invitation-btn">
                      {busy ? "Sending…" : "Send Invitation"} <Mail className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
