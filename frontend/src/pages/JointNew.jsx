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
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const isPro = user?.role === "professional";
  const isAgreement = searchParams.get("kind") === "agreement";
  const SAFETY_KEYS = ["safety", "risk", "safety_communication", "safeguards"];
  const activeSubjects = multiSubjects.length > 0 ? multiSubjects : subject ? [subject] : [];
  const isSafety = activeSubjects.length > 0 && activeSubjects.every((k) => SAFETY_KEYS.includes(k));

  useEffect(() => {
    const kind = searchParams.get("kind");
    if (kind === "agreement") {
      setSubject("co_parenting");
      setStep(1);
      return;
    }
    const single = searchParams.get("subject");
    const multi = searchParams.get("subjects");
    if (multi) {
      const keys = multi.split(",").filter(Boolean);
      setMultiSubjects(keys);
      setSubject(keys[0]);
      setStep(1);
    } else if (single) {
      setSubject(single);
      setStep(1);
    }
  }, [searchParams]);

  useEffect(() => {
    api.get("/joint/config").then((r) => setSubjects(r.data.subjects)).catch((e) => toast.error(formatApiError(e)));
    api.get("/joint/connections").then((r) => setConnections(r.data)).catch(() => {});
  }, []);

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
      const url = isAgreement ? "/joint/agreements" : isPro ? "/joint/reports/professional" : "/joint/reports";
      const body = isPro
        ? { ...base, parent_a_name: paName, parent_a_email: paEmail, parent_b_name: coName, parent_b_email: coEmail }
        : { ...base, co_parent_name: coName, co_parent_email: coEmail, mediator_email: isSafety && mediatorEmail.trim() ? mediatorEmail.trim() : undefined };
      const { data } = await api.post(url, body);
      if (isPro) {
        toast.success("Invitations sent to both parents");
        navigate("/dashboard");
      } else {
        setCreated(data);
      }
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
        {created ? (
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
              <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold mb-2">Invitation code</p>
              <div className="flex items-center gap-3">
                <span className="font-display text-3xl font-bold tracking-[0.3em]" data-testid="invitation-code-display">{created.invitation.code}</span>
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => copy(created.invitation.code)} data-testid="copy-code-btn">
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />} Copy
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                An email was sent to {created.invitation.invitee_email}. If it doesn't arrive, share this code or the invitation link directly.
              </p>
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
            <h1 className="text-4xl font-semibold mb-2" data-testid="joint-new-heading">{isAgreement ? "Create a Co-Parenting Agreement" : "Create a Joint Report"}</h1>
            <p className="text-muted-foreground mb-8">{isAgreement ? "Invite the other parent to propose terms for your joint co-parenting agreement. Each parent's proposals stay private until both are complete." : "One subject. One child. Both parents answer independently — answers stay private until both are complete."}</p>

            <div className="flex items-center gap-2 mb-10" data-testid="joint-steps">
              {["Subject", "Child", "Invite"].map((s, i) => (
                <div key={s} className="flex items-center gap-2 flex-1 last:flex-none">
                  <span className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold ${i <= step ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`} data-testid={`joint-step-${i}`}>{i + 1}</span>
                  <span className={`text-xs ${i === step ? "font-semibold" : "text-muted-foreground"}`}>{s}</span>
                  {i < 2 && <div className="flex-1 h-px bg-border mx-2" />}
                </div>
              ))}
            </div>

            {step === 0 && (
              <div data-testid="joint-step-subject">
                <h2 className="text-2xl font-semibold mb-4">What would you like the parents to explore together?</h2>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {subjects.map((s) => (
                    <button
                      key={s.key}
                      onClick={() => setSubject(s.key)}
                      className={`text-left border rounded-lg px-4 py-3 text-sm font-medium transition-colors ${subject === s.key ? "border-primary bg-secondary/60" : "border-border bg-white hover:bg-muted"}`}
                      data-testid={`subject-${s.key}`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
                {subject === "custom" && (
                  <div className="mt-4 space-y-2">
                    <Label htmlFor="custom-subject">Custom subject</Label>
                    <Input id="custom-subject" className="h-12" value={customSubject} onChange={(e) => setCustomSubject(e.target.value)} placeholder="e.g. Summer travel plans" data-testid="custom-subject-input" />
                  </div>
                )}
                <div className="mt-8 flex justify-end">
                  <Button onClick={() => setStep(1)} disabled={!subject || (subject === "custom" && !customSubject.trim())} className="gap-2" data-testid="subject-next-btn">
                    Continue <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {step === 1 && (
              <div data-testid="joint-step-child">
                <h2 className="text-2xl font-semibold mb-4">Which child is this report about?</h2>
                {multiSubjects.length > 1 && subjects.length > 0 && (
                  <p className="text-sm text-muted-foreground mb-4" data-testid="multi-subjects-line">
                    Subjects: {multiSubjects.map((k) => subjects.find((s) => s.key === k)?.label || k).join(" + ")}
                  </p>
                )}
                <div className="bg-white border border-border rounded-lg p-6 space-y-2">
                  <Label htmlFor="joint-child">Child's first name or initials</Label>
                  <Input id="joint-child" className="h-12" value={childName} onChange={(e) => setChildName(e.target.value)} placeholder="e.g. Sam" data-testid="joint-child-input" />
                </div>
                <div className="mt-8 flex justify-between">
                  <button type="button" onClick={() => setStep(0)} className="text-sm text-muted-foreground hover:text-foreground" data-testid="child-back-btn">Back</button>
                  <Button onClick={() => setStep(2)} disabled={!childName.trim()} className="gap-2" data-testid="child-next-btn">
                    Continue <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {step === 2 && (
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
                        <Label htmlFor="pa-name">Parent A first name</Label>
                        <Input id="pa-name" className="h-12" value={paName} onChange={(e) => setPaName(e.target.value)} placeholder="e.g. Ann" data-testid="parent-a-invite-name-input" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="pa-email">Parent A email</Label>
                        <Input id="pa-email" type="email" className="h-12" value={paEmail} onChange={(e) => setPaEmail(e.target.value)} placeholder="ann@example.com" data-testid="parent-a-invite-email-input" />
                      </div>
                    </>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="co-name">{isPro ? "Parent B first name" : "Co-parent's first name"}</Label>
                    <Input id="co-name" className="h-12" value={coName} onChange={(e) => setCoName(e.target.value)} placeholder="e.g. Jordan" data-testid="co-parent-name-input" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="co-email">{isPro ? "Parent B email" : "Co-parent's email"}</Label>
                    <Input id="co-email" type="email" className="h-12" value={coEmail} onChange={(e) => setCoEmail(e.target.value)} placeholder="jordan@example.com" data-testid="co-parent-email-input" />
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid="invite-privacy-note">
                    Each parent keeps a separate login. Your co-parent receives an invitation code — never share your password.
                  </p>
                </div>
                <div className="mt-6" data-testid="jointnew-confidentiality"><ConfidentialityNotice /></div>
                <div className="mt-8 flex justify-between">
                  <button type="button" onClick={() => setStep(1)} className="text-sm text-muted-foreground hover:text-foreground" data-testid="invite-back-btn">Back</button>
                  <Button onClick={submit} disabled={!coName.trim() || !coEmail.trim() || (isPro && (!paName.trim() || !paEmail.trim())) || (isSafety && !isPro && !mediatorEmail.trim()) || busy} className="gap-2" data-testid="send-invitation-btn">
                    {busy ? "Sending…" : isPro ? "Send Both Invitations" : "Send Invitation"} <Mail className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
