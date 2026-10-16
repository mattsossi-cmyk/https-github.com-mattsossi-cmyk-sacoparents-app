import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Trash2, CheckCircle2, Circle, Mail, Scale, ShieldAlert, Link2, Unlink, FileText } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { PrimaryTiles } from "@/components/dashboard/PrimaryTiles";
import { SecondaryTools } from "@/components/dashboard/SecondaryTools";
import { SafetyEntryBanner } from "@/components/SafetyEntryBanner";
import { SampleReports } from "@/components/dashboard/SampleReports";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ReminderPreviewButton } from "@/components/ReminderPreview";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import { DeleteAccountButton } from "@/components/DeleteAccount";
import { AdminProfessionals } from "@/components/AdminProfessionals";
import { AdminJudges } from "@/components/AdminJudges";
import { AdminProviders } from "@/components/AdminProviders";
import { InviteProfessional } from "@/components/InviteProfessional";
import { PendingCredentialActions } from "@/components/PendingCredentialActions";
import { CredentialUpload } from "@/components/CredentialUpload";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CourtReferralsInbox } from "@/components/CourtReferralsInbox";
import { ForcePasswordChange } from "@/components/ForcePasswordChange";
import { ParentRequestStatus } from "@/components/ParentRequestStatus";
import { CasesTable } from "@/components/CasesTable";
import { UpcomingCheckIns } from "@/components/UpcomingCheckIns";
import { ReferralInbox } from "@/components/ReferralInbox";
import { ProZipPrompt } from "@/components/ProZipPrompt";
import { ProContactCard } from "@/components/ProContactCard";
import { PublicListingCard } from "@/components/PublicListingCard";
import { AdminListings } from "@/components/AdminListings";
import { AdminAcceptanceLog } from "@/components/AdminAcceptanceLog";
import { AdminSafetyAudit } from "@/components/AdminSafetyAudit";
import { AdminWebhookCheck } from "@/components/AdminWebhookCheck";
import { InviteReminderPanel } from "@/components/InviteReminderPanel";
import { SenderStatusBadge } from "@/components/SenderStatusBadge";
import { ProTopNav } from "@/components/dashboard/ProTopNav";
import { ProHero } from "@/components/dashboard/ProHero";
import { PipelineStepper } from "@/components/dashboard/PipelineStepper";
import { AlignAssistant } from "@/components/AlignAssistant";
import { SampleTour, useSampleTour, TourButton, PRO_TOUR } from "@/components/SampleTour";

export default function Dashboard() {
  const [cases, setCases] = useState(null);
  const [joints, setJoints] = useState(null);
  const [connections, setConnections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [showProForm, setShowProForm] = useState(false);
  const [professionals, setProfessionals] = useState([]);
  const [proRequests, setProRequests] = useState([]);
  const [proForm, setProForm] = useState({ professional_email: "", child_name: "", co_parent_name: "" });
  const [prepEmails, setPrepEmails] = useState({});
  const [extLink, setExtLink] = useState(null);
  const [linkCode, setLinkCode] = useState("");
  const { user, logout, refresh } = useAuth();
  const isPro = user?.role === "professional" || user?.role === "admin";
  const [pendingPros, setPendingPros] = useState([]);
  const [declinedPros, setDeclinedPros] = useState([]);
  const [showDeclined, setShowDeclined] = useState(false);
  const [courtRefs, setCourtRefs] = useState(null);
  const loadCourtRefs = () => api.get("/professional/court-referrals").then((r) => setCourtRefs(r.data)).catch(() => setCourtRefs([]));
  useEffect(() => { if (isPro) loadCourtRefs(); }, [isPro]);

  const realCases = (joints || []).filter((j) => j.is_creator && !j.archived && !j.is_demo);
  const readyCount = realCases.filter((j) => j.case_status === "READY_FOR_ALIGNMENT" || j.case_status === "REPORT_GENERATED").length;
  const pendingReferrals = (courtRefs || []).filter((x) => x.status === "pending").length;
  const awaitingSubmit = (courtRefs || []).filter((x) => x.status === "accepted").length;
  const overdueCount = (courtRefs || []).filter((x) => x.overdue).length;
  const heroCounts = {
    awaitingParents: realCases.filter((j) => ["DRAFT", "INVITED", "ONE_COMPLETE"].includes(j.case_status)).length,
    assessmentsIn: realCases.filter((j) => ["ONE_COMPLETE", "READY_FOR_ALIGNMENT"].includes(j.case_status)).length,
    jointReady: readyCount,
    lensReady: realCases.filter((j) => j.case_status === "REPORT_GENERATED").length,
    courtPending: awaitingSubmit, overdue: overdueCount, referrals: pendingReferrals,
  };
  const [selectedCase, setSelectedCase] = useState(null);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [trigger, setTrigger] = useState(null);
  const activeCase = realCases.find((j) => j.id === selectedCase) || realCases[0] || null;
  const fireTrigger = (key, mode) => setTrigger({ key, mode, at: Date.now() });
  const reportCase = realCases.find((j) => j.id === activeCase?.id && j.status === "ready") || realCases.find((j) => j.status === "ready" && j.kind !== "agreement" && j.kind !== "foundation");
  const reviewTo = activeCase ? `/joint/${activeCase.id}` : "#cases";
  const reportTo = reportCase ? `/cases/${reportCase.id}/professional-report` : "#cases";
  const proTour = useSampleTour(Boolean(isPro && user?.approved !== false && joints !== null), `pro-tour-${user?.id || "anon"}`);
  const proTourSteps = PRO_TOUR.filter((s) => s.id !== "pipeline-stepper" || realCases.length > 0);
  useEffect(() => { if (new URLSearchParams(window.location.search).get("tour") === "1" && isPro && joints !== null) proTour.start(); }, [isPro, joints]); // eslint-disable-line react-hooks/exhaustive-deps

  const closeCase = async (j) => {
    const note = window.prompt(`Close case ${j.case_code || ""}? It moves to the archive and stays available for records. Optional closing note:`);
    if (note === null) return;
    try {
      await api.patch(`/joint/reports/${j.id}/close`, { closed: true, note });
      toast.success("Case closed");
      setJoints((prev) => prev.map((x) => (x.id === j.id ? { ...x, archived: true, closed_at: new Date().toISOString(), case_status: "CLOSED" } : x)));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  useEffect(() => {
    if (user?.role === "admin") {
      api.get("/admin/pending-professionals").then((r) => setPendingPros(r.data)).catch(() => {});
      api.get("/admin/declined-professionals").then((r) => setDeclinedPros(r.data)).catch(() => {});
    }
  }, [user]);

  const reconsiderPro = async (p) => {
    try {
      await api.post(`/admin/reconsider-professional/${p.id}`);
      toast.success("Moved back to pending approvals");
      setDeclinedPros((prev) => prev.filter((d) => d.id !== p.id));
      setPendingPros((prev) => [{ ...p, verification_level: "credentials_pending" }, ...prev]);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const approvePro = async (id) => {
    try {
      await api.post(`/admin/approve-professional/${id}`);
      toast.success("Professional approved");
      setPendingPros((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };
  const [declining, setDeclining] = useState(null);
  const [declineReason, setDeclineReason] = useState("");
  const declinePro = async (id) => {
    try {
      await api.post(`/admin/decline-professional/${id}`, { reason: declineReason });
      toast.success("Registration declined");
      const declined = pendingPros.find((p) => p.id === id);
      if (declined) setDeclinedPros((prev) => [{ ...declined, declined_reason: declineReason, declined_at: new Date().toISOString() }, ...prev]);
      setPendingPros((prev) => prev.filter((p) => p.id !== id));
      setDeclining(null);
      setDeclineReason("");
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const load = () => {
    api.get("/cases").then((r) => setCases(r.data)).catch((e) => toast.error(formatApiError(e)));
    api.get("/joint/reports").then((r) => setJoints(r.data)).catch(() => setJoints([]));
    api.get("/joint/connections").then((r) => setConnections(r.data)).catch(() => {});
    api.get("/joint/config").then((r) => setSubjects(r.data.subjects)).catch(() => {});
    api.get("/joint/professional-requests").then((r) => setProRequests(r.data)).catch(() => {});
    api.get("/external/link").then((r) => setExtLink(r.data)).catch(() => setExtLink({ linked: false }));
  };

  useEffect(load, []);

  const [sampleLoading, setSampleLoading] = useState(false);
  const loadSample = async () => {
    setSampleLoading(true);
    try {
      const { data } = await api.post("/joint/reports/professional/sample");
      toast.success(data.already_existed ? "Your sample case is already on your dashboard" : `Sample case ${data.case_code} added`);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSampleLoading(false); }
  };


  const acceptCode = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/joint/invitations/accept", { code: code.trim() });
      toast.success("Invitation accepted");
      navigate(`/joint/${data.report_id}/assess`);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const linkAccount = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/external/link", { code: linkCode.trim() });
      toast.success(`Linked to ${data.external_email}`);
      setLinkCode("");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const unlinkAccount = async () => {
    try {
      await api.delete("/external/link");
      toast.success("Account unlinked");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const resend = async (iid) => {
    try {
      await api.post(`/joint/invitations/${iid}/resend`);
      toast.success("Invitation resent");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const cancelInv = async (iid) => {
    try {
      await api.post(`/joint/invitations/${iid}/cancel`);
      toast.success("Invitation cancelled");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const changeSubject = async (iid, subject) => {
    try {
      await api.patch(`/joint/invitations/${iid}`, { subject });
      toast.success("Subject updated");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  useEffect(() => {
    if (searchParams.get("contact") === "professional" && !showProForm) openProForm();
  }, [searchParams]);

  const openProForm = async () => {
    setShowProForm(!showProForm);
    if (!showProForm && professionals.length === 0) {
      try {
        const { data } = await api.get("/professionals");
        setProfessionals(data);
      } catch (e) { toast.error(formatApiError(e)); }
    }
  };

  const submitProRequest = async () => {
    setBusy(true);
    try {
      await api.post("/joint/professional-requests", proForm);
      toast.success("Request sent to the professional");
      setShowProForm(false);
      setProForm({ professional_email: "", child_name: "", co_parent_name: "" });
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const prepareRequest = async (reqId) => {
    const emails = prepEmails[reqId] || {};
    const payload = emails.a?.trim() && emails.b?.trim() ? { parent_a_email: emails.a.trim(), parent_b_email: emails.b.trim() } : undefined;
    try {
      const { data } = await api.post(`/joint/professional-requests/${reqId}/prepare`, payload);
      toast.success("Assessment prepared — invitations sent to both parents");
      navigate(`/joint/${data.report_id}`);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/cases/${id}`);
      toast.success("Assessment deleted");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const legacyTools = (
    <>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 min-w-0" data-testid="tools-grid">
          <div className="bg-white border border-border rounded-lg p-6 min-w-0" data-testid="individual-tools-card">
            <p className="text-xs uppercase tracking-widest text-brand-teal font-bold">Individual Assessments</p>
            <h2 className="text-2xl font-semibold mt-1">Import from sacoparentsapp.online</h2>
            <p className="text-sm text-muted-foreground mt-2 mb-5">Individual assessments are completed in the SA CoParents app. Link once — your completed assessments are pulled into your Joint Reports automatically.</p>
            {extLink?.linked ? (
              <div data-testid="ext-linked-block">
                <p className="text-sm" data-testid="ext-linked-email">Linked: <span className="font-semibold">{extLink.external_email}</span></p>
                <p className="text-xs text-muted-foreground mt-1">Imported material stays private to you and is only used inside Joint Report comparisons.</p>
                <Button variant="ghost" size="sm" className="mt-3 gap-1.5 text-destructive" onClick={unlinkAccount} data-testid="ext-unlink-btn"><Unlink className="h-3.5 w-3.5" /> Unlink account</Button>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row gap-2" data-testid="ext-link-block">
                <Input value={linkCode} onChange={(e) => setLinkCode(e.target.value.toUpperCase())} placeholder="Link code from sacoparentsapp.online" className="h-11 uppercase tracking-widest" maxLength={8} data-testid="ext-link-code-input" />
                <Button onClick={linkAccount} disabled={linkCode.trim().length !== 8 || busy} className="h-11 gap-1.5" data-testid="ext-link-btn"><Link2 className="h-4 w-4" /> Link</Button>
              </div>
            )}
          </div>
          <div className="bg-white border-2 border-primary/30 rounded-lg p-6 min-w-0" data-testid="joint-tools-card">
            <p className="text-xs uppercase tracking-widest text-primary font-bold">Joint Tools</p>
            {isPro ? (
              <>
                <h2 className="text-2xl font-semibold mt-1">Create a Joint Report</h2>
                <p className="text-sm text-muted-foreground mt-2 mb-5">Compare perspectives. Find alignment. Identify issues that may need discussion.</p>
                <Link to="/joint/new" data-testid="create-joint-report-link">
                  <Button className="gap-2 h-auto whitespace-normal text-left" data-testid="create-joint-report-btn"><Mail className="h-4 w-4 shrink-0" /> Create a Professional Alignment Case</Button>
                </Link>
                <Link to="/hub" className="block mt-3 text-sm text-primary font-medium hover:underline" data-testid="open-hub-link">
                  Open the Joint Report Hub →
                </Link>
              </>
            ) : (
              <>
                <h2 className="text-2xl font-semibold mt-1">Joint Reports</h2>
                <p className="text-sm text-muted-foreground mt-2" data-testid="parent-joint-note">Joint reports are initiated by an authorized professional. When you're invited, enter your case code below or use the secure link in your invitation email.</p>
              </>
            )}
          </div>
        </div>

        <div className={isPro ? "grid md:grid-cols-2 gap-4" : "grid gap-4"} data-testid="agreement-tools-grid">
          {!isPro && (
          <div className="bg-white border border-border rounded-lg p-6 min-w-0" data-testid="foundation-card">
            <p className="text-xs uppercase tracking-widest text-brand-teal font-bold">Child-Focused Foundation Statement</p>
            <h2 className="text-2xl font-semibold mt-1">Write your Foundation Statement</h2>
            <p className="text-sm text-muted-foreground mt-2 mb-5">Your goals, priorities, concerns and commitments for your child — in your own words. Private until you share it into a case, then downloadable as a branded PDF.</p>
            <div className="flex flex-wrap gap-2">
              <Link to="/foundation" data-testid="foundation-write-link"><Button className="gap-2" data-testid="foundation-write-btn"><FileText className="h-4 w-4" /> Write / edit my statement</Button></Link>
              <Link to="/samples/foundation-statement" data-testid="foundation-sample-link"><Button variant="outline">See a sample</Button></Link>
            </div>
          </div>
          )}
          {isPro && (
          <div className="bg-white border border-border rounded-lg p-6 min-w-0" data-testid="agreement-card">
            <p className="text-xs uppercase tracking-widest text-brand-teal font-bold">Co-Parenting Agreement</p>
            <h2 className="text-2xl font-semibold mt-1">Create a Joint Agreement</h2>
            <p className="text-sm text-muted-foreground mt-2 mb-5">Invite the other parent to create the joint co-parenting agreement — each parent proposes terms privately.</p>
            <Link to="/joint/new?kind=agreement" data-testid="create-agreement-link">
              <Button variant="outline" className="gap-2 h-auto whitespace-normal text-left" data-testid="create-agreement-btn"><Scale className="h-4 w-4 shrink-0" /> Invite Co-Parent to Joint Agreement</Button>
            </Link>
          </div>
          )}
          <div className="bg-white border-2 border-red-200 rounded-lg p-6 min-w-0" data-testid="fv-contact-card">
            <p className="text-xs uppercase tracking-widest text-red-700 font-bold">Family Violence Pathway</p>
            <h2 className="text-2xl font-semibold mt-1">Contact a Professional</h2>
            <p className="text-sm text-muted-foreground mt-2 mb-5">A designated professional prepares the joint family violence co-parenting assessment — no need to provide the other parent's email. Responses are never shared between the parties.</p>
            <Button onClick={openProForm} className="gap-2 bg-red-700 hover:bg-red-800 text-white" data-testid="contact-professional-btn">
              <ShieldAlert className="h-4 w-4" /> Contact a Professional
            </Button>
            {showProForm && (
              <div className="mt-5 pt-4 border-t border-red-100 space-y-3" data-testid="pro-contact-form">
                <select
                  className="w-full h-11 rounded-md border border-input bg-white px-3 text-sm"
                  value={proForm.professional_email}
                  onChange={(e) => setProForm({ ...proForm, professional_email: e.target.value })}
                  data-testid="pro-select"
                >
                  <option value="">Choose a registered professional…</option>
                  {professionals.map((p) => (
                    <option key={p.email} value={p.email}>{p.name} ({p.email})</option>
                  ))}
                </select>
                <Input placeholder="Child's first name or initials" value={proForm.child_name} onChange={(e) => setProForm({ ...proForm, child_name: e.target.value })} data-testid="pro-child-input" />
                <Input placeholder="Other parent's first name (optional)" value={proForm.co_parent_name} onChange={(e) => setProForm({ ...proForm, co_parent_name: e.target.value })} data-testid="pro-coparent-name-input" />
                <p className="text-xs text-muted-foreground" data-testid="pro-privacy-note">No need for the other parent's email — the professional collects both parents' details privately. Responses are never shared between the parties.</p>
                <Button
                  onClick={submitProRequest}
                  disabled={!proForm.professional_email || !proForm.child_name.trim() || busy}
                  className="w-full bg-red-700 hover:bg-red-800 text-white"
                  data-testid="pro-request-submit-btn"
                >
                  {busy ? "Sending…" : "Send Request to Professional"}
                </Button>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white border border-border rounded-lg p-6" data-testid="enter-code-card">
          <p className="font-semibold mb-1">Already invited?</p>
          <p className="text-sm text-muted-foreground mb-4">Enter the invitation code from your email to join a Joint Report.</p>
          <div className="flex gap-2 max-w-md">
            <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="e.g. SA-26-EDU-K7M4Q2" className="h-12 tracking-[0.2em] uppercase font-semibold" maxLength={16} data-testid="invitation-code-input" />
            <Button onClick={acceptCode} disabled={code.trim().length < 6 || busy} className="h-12" data-testid="accept-invitation-btn">Accept</Button>
          </div>
        </div>
    </>
  );

  return (
    <div className="min-h-screen bg-background" data-testid="dashboard-page">
      {user?.must_change_password && <ForcePasswordChange onDone={refresh} />}
      <header className="bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-3">
          <Link to="/" data-testid="dash-brand-link" className="min-w-0 shrink">
            <BrandLogo />
          </Link>
          {isPro && <div className="hidden lg:block flex-1 px-4"><ProTopNav cases={realCases} /></div>}
          <div className="flex items-center gap-2 sm:gap-4 shrink-0">
            <span className="text-sm hidden 2xl:block" data-testid="user-email"><span className="font-medium" data-testid="user-name">{user?.name}</span>{user?.name ? <span className="text-muted-foreground"> · {user?.email}</span> : <span className="text-muted-foreground">{user?.email}</span>}</span>
            {user?.credentials_verified && <span className="hidden sm:inline-flex"><VerifiedBadge /></span>}
            {user?.role === "parent" && <DeleteAccountButton onDeleted={refresh} />}
            <Button variant="outline" size="sm" onClick={async () => { await logout(); navigate("/"); }} data-testid="logout-btn">
              Sign out
            </Button>
          </div>
        </div>
      </header>
      {user?.role === "parent" && <SafetyEntryBanner />}

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 space-y-12 overflow-x-hidden">
        {isPro ? (
          <>
            <div className="lg:hidden"><ProTopNav cases={realCases} /></div>
            <div className="flex justify-end"><TourButton onClick={proTour.start} testId="pro-tour-start-btn" /></div>
            {proTour.open && <SampleTour steps={proTourSteps} storageKey={`pro-tour-${user?.id || "anon"}`} onDone={proTour.close} label="Dashboard tour" prefix="pro-tour" />}
            <ProHero counts={heroCounts} reviewTo={reviewTo} reportTo={reportTo} onTrigger={fireTrigger} />
            <PipelineStepper cases={realCases} selectedId={activeCase?.id} onSelect={setSelectedCase} onTrigger={fireTrigger} />
            <AlignAssistant userId={user?.id || "anon"} caseId={activeCase?.id} caseLabel={activeCase?.case_code} trigger={trigger} open={assistantOpen} onOpenChange={setAssistantOpen} />
          </>
        ) : (
          <div>
            <h1 className="text-4xl font-semibold" data-testid="dash-heading">Dashboard</h1>
            <p className="text-muted-foreground mt-2" data-testid="dash-subtext">Joint reports are initiated by your professional. Use your invitation link or case code to take part.</p>
          </div>
        )}

        {isPro && user?.role === "professional" && <ProZipPrompt />}
        {isPro && <ProContactCard />}
        {isPro && <InviteReminderPanel />}
        {isPro && user?.role === "professional" && <PublicListingCard />}

        {isPro && user?.approved === false && (
          <div className="bg-align-yellow/10 border border-align-yellow/40 rounded-lg p-5 mb-6" data-testid="approval-pending-banner">
            <p className="font-semibold">Your professional account is pending approval</p>
            <p className="text-sm text-muted-foreground mt-1">SA CoParents reviews new professional accounts before they can create Professional Alignment Cases. You'll receive an email once approved.</p>
          </div>
        )}

        {user?.role === "admin" && (
          <Tabs defaultValue="invite" className="mb-6" data-testid="admin-tabs">
            <div className="mb-2 flex justify-end"><SenderStatusBadge /></div>
            <TabsList className="flex flex-wrap h-auto gap-1 bg-white border border-border p-1">
              <TabsTrigger value="invite" data-testid="admin-tab-invite">Invite Professional</TabsTrigger>
              <TabsTrigger value="pending" data-testid="admin-tab-pending">Pending Credentials{pendingPros.length ? <span className="ml-1 rounded-full bg-align-yellow px-1.5 text-[10px] font-bold text-black">{pendingPros.length}</span> : null}</TabsTrigger>
              <TabsTrigger value="approved" data-testid="admin-tab-approved">Approved Professionals</TabsTrigger>
              <TabsTrigger value="judges" data-testid="admin-tab-judges">Judges</TabsTrigger>
              <TabsTrigger value="providers" data-testid="admin-tab-providers">Provider Directory</TabsTrigger>
              <TabsTrigger value="listings" data-testid="admin-tab-listings">Public Listings</TabsTrigger>
              <TabsTrigger value="acceptance" data-testid="admin-tab-acceptance">Acceptance Log</TabsTrigger>
            </TabsList>
            <TabsContent value="invite"><InviteProfessional /></TabsContent>
            <TabsContent value="pending">
          <section className="bg-white border-2 border-align-yellow/50 rounded-lg p-6 mb-6" data-testid="admin-approvals-section">
            <h2 className="text-lg font-semibold">Pending Credentials &amp; Approvals</h2>
            {pendingPros.length === 0 ? (
              <p className="text-sm text-muted-foreground mt-2" data-testid="admin-approvals-empty">No professionals awaiting approval.</p>
            ) : (
              <ul className="mt-3 space-y-2" data-testid="admin-approvals-list">
                {pendingPros.map((p) => (
                  <li key={p.id} className="flex items-start justify-between gap-3 border border-border rounded-md px-4 py-3" data-testid={`pending-pro-${p.id}`}>
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{p.name}</p>
                      <p className="text-xs text-muted-foreground">{p.email}{p.profile?.phone ? ` · ${p.profile.phone}` : ""}</p>
                      <dl className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-1 text-xs">
                        <div data-testid={`pending-pro-role-${p.id}`}><dt className="text-muted-foreground">Role</dt><dd className="font-medium">{p.profile?.pro_role || "Not provided"}</dd></div>
                        <div data-testid={`pending-pro-org-${p.id}`}><dt className="text-muted-foreground">Organization</dt><dd className="font-medium">{p.profile?.organization || "Not provided"}{(p.profile?.city || p.profile?.state) ? ` (${[p.profile.city, p.profile.state].filter(Boolean).join(", ")})` : ""}</dd></div>
                        <div data-testid={`pending-pro-license-${p.id}`}><dt className="text-muted-foreground">License / Credential</dt><dd className="font-medium">{p.profile?.license_number || "Not provided"}</dd></div>
                      </dl>
                      {p.profile?.website && <a href={p.profile.website} target="_blank" rel="noreferrer" className="text-xs text-align-teal underline mt-1 inline-block" data-testid={`pending-pro-website-${p.id}`}>{p.profile.website}</a>}
                      {p.created_at && <p className="text-[11px] text-muted-foreground mt-1">Registered {new Date(p.created_at).toLocaleDateString()}</p>}
                      <PendingCredentialActions pro={p} onAccepted={(id) => setPendingPros((prev) => prev.filter((x) => x.id !== id))} />
                    </div>
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => approvePro(p.id)} data-testid={`approve-pro-btn-${p.id}`}>Approve</Button>
                        <Button size="sm" variant="outline" className="text-destructive border-destructive/40" onClick={() => { setDeclining(declining === p.id ? null : p.id); setDeclineReason(""); }} data-testid={`decline-pro-btn-${p.id}`}>Decline</Button>
                      </div>
                      {declining === p.id && (
                        <div className="flex gap-2 w-72" data-testid={`decline-form-${p.id}`}>
                          <Input value={declineReason} onChange={(e) => setDeclineReason(e.target.value)} placeholder="Brief reason (sent to applicant)" maxLength={500} data-testid={`decline-reason-input-${p.id}`} />
                          <Button size="sm" variant="destructive" disabled={!declineReason.trim()} onClick={() => declinePro(p.id)} data-testid={`decline-confirm-btn-${p.id}`}>Confirm</Button>
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-5 border-t border-border pt-4" data-testid="declined-log-section">
              <button onClick={() => setShowDeclined((v) => !v)} className="text-sm font-medium text-primary hover:underline" data-testid="declined-log-toggle">
                {showDeclined ? "Hide" : "Show"} declined registrations ({declinedPros.length})
              </button>
              {showDeclined && (
                declinedPros.length === 0 ? (
                  <p className="text-xs text-muted-foreground mt-2" data-testid="declined-log-empty">No declined registrations.</p>
                ) : (
                  <ul className="mt-3 space-y-2" data-testid="declined-log-list">
                    {declinedPros.map((p) => (
                      <li key={p.id} className="flex items-start justify-between gap-3 border border-border rounded-md px-4 py-3 bg-muted/30" data-testid={`declined-pro-${p.id}`}>
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{p.name} <span className="text-muted-foreground font-normal">· {p.email}</span></p>
                          <p className="text-xs text-muted-foreground">{[p.profile?.pro_role, p.profile?.organization, p.profile?.license_number].filter(Boolean).join(" · ") || "No profile details"}</p>
                          <p className="text-xs mt-1" data-testid={`declined-reason-${p.id}`}><span className="text-muted-foreground">Reason:</span> {p.declined_reason}</p>
                          {p.declined_at && <p className="text-[11px] text-muted-foreground mt-0.5">Declined {new Date(p.declined_at).toLocaleDateString()}</p>}
                        </div>
                        <Button size="sm" variant="outline" onClick={() => reconsiderPro(p)} data-testid={`reconsider-pro-btn-${p.id}`}>Reconsider</Button>
                      </li>
                    ))}
                  </ul>
                )
              )}
            </div>
          </section>
            </TabsContent>
            <TabsContent value="approved"><AdminProfessionals /></TabsContent>
            <TabsContent value="listings"><AdminListings /></TabsContent>
            <TabsContent value="judges"><AdminJudges /></TabsContent>
            <TabsContent value="providers"><AdminProviders /></TabsContent>
            <TabsContent value="acceptance">
              <h3 className="mb-3 text-base font-bold md:text-lg" data-testid="privacy-log-heading">Privacy Notification — parents and professionals</h3>
              <AdminAcceptanceLog />
              <AdminSafetyAudit />
              <AdminWebhookCheck />
              <h3 className="mb-3 mt-10 text-base font-bold md:text-lg" data-testid="pro-notice-log-heading">Professional Notice, Confidentiality &amp; Safety Warning — professionals</h3>
              <AdminAcceptanceLog endpoint="/admin/professional-notice/acceptances" filename="professional-notice-acceptances.csv" label="professional notice" testId="admin-pro-notice-log" />
            </TabsContent>
          </Tabs>
        )}

        {isPro && user?.role === "professional" && <CredentialUpload user={user} />}

        {connections.length > 0 && (
          <div data-testid="connections-section">
            <h2 className="text-2xl font-semibold mb-4">Connected for Joint Assessments</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {connections.map((c) => (
                <div key={c.id} className="bg-secondary/50 border border-border rounded-lg p-5" data-testid={`connection-${c.id}`}>
                  <p className="font-semibold">You and {c.other_name} are connected{c.child_name ? ` for reports concerning ${c.child_name}` : ""}.</p>
                  <p className="text-sm text-muted-foreground mt-1">Individual reflections remain separate. Only information designated for the Joint Report is compared.</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {isPro && (
          <>
            <section id="cases" className="scroll-mt-6" data-testid="joint-reports-section">
              <h2 className="text-2xl font-semibold mb-4">Your Cases</h2>
              {joints === null ? (
                <p className="text-muted-foreground" data-testid="joints-loading">Loading…</p>
              ) : realCases.length === 0 ? (
                <p className="text-sm text-muted-foreground" data-testid="joints-empty">No client cases yet. Use <Link to="/joint/new" className="text-primary underline">Invite Parents</Link> to open your first case.</p>
              ) : (
                <>
                  <UpcomingCheckIns cases={realCases} />
                  <CasesTable cases={realCases} onClose={closeCase} />
                </>
              )}
            </section>
            <CourtReferralsInbox refs={courtRefs} onChange={loadCourtRefs} alwaysShow />
            {user?.approved !== false && <SampleReports cases={joints} onLoadSample={loadSample} loading={sampleLoading} canLoad />}
          </>
        )}

        {isPro && (
          <details className="rounded-lg border border-border bg-white" data-testid="more-tools">
            <summary className="cursor-pointer select-none px-6 py-4 text-sm font-semibold" data-testid="more-tools-toggle">More tools — app account link, joint agreements, family violence pathway, invitation codes</summary>
            <div className="border-t border-border p-6 space-y-6">
              <PrimaryTiles activeCount={realCases.length} readyCount={readyCount} referralCount={pendingReferrals} submitCount={awaitingSubmit} overdueCount={overdueCount} />
              <SecondaryTools />
              {legacyTools}
            </div>
          </details>
        )}

        {!isPro && legacyTools}

        {!isPro && (
        <div data-testid="joint-reports-section">
          <h2 className="text-2xl font-semibold mb-4">Joint Reports</h2>
          {joints === null ? (
            <p className="text-muted-foreground" data-testid="joints-loading">Loading…</p>
          ) : joints.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="joints-empty">No joint reports yet. Use your invitation link or case code above.</p>
          ) : (
            <>
            <div className="grid md:grid-cols-2 gap-4" data-testid="joints-grid">
              {joints.filter((j) => !j.archived).map((j) => {
                const ready = j.status === "ready";
                const pending = j.pending_invitations || (j.invitation && j.invitation.status === "pending" ? [j.invitation] : []);
                const myP = j.my_role ? j.participants[j.my_role] : null;
                const otherP = j.my_role ? j.participants[j.my_role === "a" ? "b" : "a"] : null;
                const rows = j.my_role
                  ? [["Your assessment", myP], ["Other parent's assessment", otherP]]
                  : [[`${j.participants.a.name || "Parent A"}'s assessment`, j.participants.a], [`${j.participants.b.name || "Parent B"}'s assessment`, j.participants.b]];
                return (
                  <div key={j.id} className="bg-white border border-border rounded-lg p-6" data-testid={`joint-card-${j.id}`}>
                    <p className="text-xs uppercase tracking-widest text-accent font-semibold">{j.subject_label}</p>
                    <h3 className="text-xl font-semibold mt-1" data-testid={`joint-title-${j.id}`}>{j.child_name ? `For ${j.child_name}` : "Joint Report"}</h3>
                    {j.professional_name && <p className="text-xs text-muted-foreground mt-1">Created by {j.professional_name} (professional)</p>}
                    {j.case_code && <p className="text-xs text-muted-foreground mt-1" data-testid={`joint-case-code-${j.id}`}>Alignment Case: <span className="font-semibold tracking-widest">{j.case_code}</span></p>}
                    {j.case_reference && <p className="text-xs text-muted-foreground mt-1" data-testid={`joint-case-ref-${j.id}`}>Your case reference: {j.case_reference} (private to you)</p>}
                    <div className="mt-4 space-y-2 text-sm">
                      {rows.map(([label, p]) => (
                        <div key={label} className="flex items-center gap-2" data-testid={`joint-row-${j.id}-${label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
                          {p.completed ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                          <span>{label}: {p.completed ? (p.imported ? "Complete (imported)" : "Complete") : p.accepted ? "In progress" : "Awaiting completion"}</span>
                        </div>
                      ))}
                      <div className="flex items-center gap-2" data-testid={`joint-report-status-${j.id}`}>
                        {ready ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                        <span className={ready ? "font-semibold" : ""}>Joint Report: {ready ? "Ready" : "Waiting for both parents"}</span>
                      </div>
                    </div>
                    <div className="mt-5 flex flex-wrap gap-2 items-center">
                      {myP && !myP.completed && myP.accepted && (
                        <Link to={j.kind === "foundation" ? `/foundation?case=${j.id}` : `/joint/${j.id}/assess`} data-testid={`joint-complete-link-${j.id}`}>
                          <Button size="sm" data-testid={`joint-complete-btn-${j.id}`}>{j.kind === "foundation" ? "Write My Foundation Statement" : "Complete My Assessment"}</Button>
                        </Link>
                      )}
                      {(ready || (myP && myP.completed) || !j.my_role) && (
                        <Link to={`/joint/${j.id}`} data-testid={`joint-view-link-${j.id}`}>
                          <Button size="sm" variant={ready ? "default" : "secondary"} data-testid={`joint-view-btn-${j.id}`}>{ready ? (j.my_role ? "View Joint Report" : "Generate Report") : "View Status"}</Button>
                        </Link>
                      )}
                      {j.is_creator && pending.length > 0 && (
                        <>
                          {pending.map((pi) => (
                            <ReminderPreviewButton
                              key={pi.id}
                              iid={pi.id}
                              label={pending.length > 1 ? `Send Reminder — ${pi.invitee_name || `Parent ${pi.role.toUpperCase()}`}` : "Send Reminder"}
                              testId={pending.length > 1 ? `joint-remind-btn-${j.id}-${pi.role}` : `joint-resend-btn-${j.id}`}
                            />
                          ))}
                          <select
                            className="h-9 rounded-md border border-input bg-white px-2 text-sm"
                            value={j.subject}
                            onChange={(e) => changeSubject(pending[0].id, e.target.value)}
                            data-testid={`joint-change-subject-${j.id}`}
                          >
                            {subjects.map((s) => (
                              <option key={s.key} value={s.key}>{s.label}</option>
                            ))}
                          </select>
                          <Button size="sm" variant="ghost" className="text-destructive" onClick={() => cancelInv(pending[0].id)} data-testid={`joint-cancel-btn-${j.id}`}>Cancel Invitation</Button>
                        </>
                      )}
                    </div>
                    {j.is_creator && j.invitation && j.invitation.status === "pending" && (
                      <p className="mt-3 text-xs text-muted-foreground" data-testid={`joint-code-${j.id}`}>
                        Invitation code for {j.invitation.invitee_email}: <span className="font-semibold tracking-widest">{j.invitation.code}</span>
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
            </>
          )}
        </div>
        )}

        {isPro && (joints || []).some((j) => j.shared_with_me) && (
          <div className="mb-10" data-testid="shared-with-me-section">
            <h2 className="text-2xl font-semibold mb-4">Shared With Me</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {(joints || []).filter((j) => j.shared_with_me).map((j) => (
                <Link key={j.id} to={`/joint/${j.id}`} className="block" data-testid={`shared-report-${j.id}`}>
                  <div className="bg-white border border-border rounded-lg p-6 hover:shadow-md transition-shadow">
                    <p className="text-xs uppercase tracking-widest text-brand-teal font-bold">{j.subject_label}</p>
                    <h3 className="text-xl font-semibold mt-1">For {j.child_name}</h3>
                    <p className="text-sm text-muted-foreground mt-2">Shared by the parents — open to review the completed report.</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {!isPro && <ParentRequestStatus requests={proRequests} />}

        {isPro && user?.approved !== false && <ReferralInbox />}

        {isPro && proRequests.length > 0 && (
          <div data-testid="pro-requests-section">
            <h2 className="text-2xl font-semibold mb-4">Facilitation Requests</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {proRequests.map((r) => (
                <div key={r.id} className="bg-white border border-red-200 rounded-lg p-6" data-testid={`pro-request-${r.id}`}>
                  <p className="text-xs uppercase tracking-widest text-red-700 font-semibold">Family Violence Assessment</p>
                  <h3 className="text-xl font-semibold mt-1">{r.child_name ? `For ${r.child_name}` : "Joint Assessment"}</h3>
                  <p className="text-sm text-muted-foreground mt-2">{r.parent_name} ({r.parent_email}){r.co_parent_email ? <> and {r.co_parent_name || "the other parent"} ({r.co_parent_email})</> : " — the other parent's details are collected privately at preparation"}</p>
                  <p className="text-xs text-muted-foreground mt-1" data-testid={`pro-request-status-${r.id}`}>Status: {r.status}</p>
                  {r.status === "pending" && (
                    <div className="mt-4 space-y-2">
                      {!r.co_parent_email && (
                        <>
                          <Input type="email" placeholder="First parent's email" value={prepEmails[r.id]?.a || ""} onChange={(e) => setPrepEmails({ ...prepEmails, [r.id]: { ...prepEmails[r.id], a: e.target.value } })} data-testid={`pro-prepare-email-a-${r.id}`} />
                          <Input type="email" placeholder="Other parent's email" value={prepEmails[r.id]?.b || ""} onChange={(e) => setPrepEmails({ ...prepEmails, [r.id]: { ...prepEmails[r.id], b: e.target.value } })} data-testid={`pro-prepare-email-b-${r.id}`} />
                        </>
                      )}
                      <Button size="sm" className="bg-red-700 hover:bg-red-800 text-white" onClick={() => prepareRequest(r.id)} disabled={!r.co_parent_email && !(prepEmails[r.id]?.a?.trim() && prepEmails[r.id]?.b?.trim())} data-testid={`pro-prepare-btn-${r.id}`}>
                        Prepare Assessment
                      </Button>
                      <p className="text-xs text-muted-foreground" data-testid={`pro-prepare-note-${r.id}`}>Each parent receives their own private assessment link — responses are never shared between the parties.</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {cases !== null && cases.length > 0 && (
        <div data-testid="assessments-section">
          <h2 className="text-2xl font-semibold mb-4">Previous Private Assessments</h2>
          <p className="text-sm text-muted-foreground mb-4">Created before individual assessments moved to sacoparentsapp.online.</p>
          {(
            <div className="grid md:grid-cols-2 gap-4" data-testid="cases-grid">
              {cases.map((c) => {
                const ready = c.has_a && c.has_b;
                return (
                  <div key={c.id} className="bg-white border border-border rounded-lg p-6" data-testid={`case-card-${c.id}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-widest text-accent font-semibold">{c.type_title}</p>
                        <h3 className="text-xl font-semibold mt-1" data-testid={`case-title-${c.id}`}>
                          {c.child_name ? `For ${c.child_name}` : "Joint Assessment"}
                        </h3>
                      </div>
                      {c.is_demo && (
                        <span className="text-xs bg-secondary text-secondary-foreground px-2 py-1 rounded" data-testid={`case-demo-badge-${c.id}`}>Demo</span>
                      )}
                    </div>
                    <div className="mt-4 space-y-2 text-sm">
                      <div className="flex items-center gap-2" data-testid={`case-status-a-${c.id}`}>
                        {c.has_a ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                        <span>{c.parent_a_name}: {c.has_a ? "Assessment completed" : "Not completed"}</span>
                      </div>
                      <div className="flex items-center gap-2" data-testid={`case-status-b-${c.id}`}>
                        {c.has_b ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                        <span>{c.parent_b_name}: {c.has_b ? "Assessment completed" : "Not completed"}</span>
                      </div>
                    </div>
                    <div className="mt-5 flex flex-wrap gap-2">
                      {ready && (
                        <Link to={`/report/${c.id}`} data-testid={`case-report-link-${c.id}`}>
                          <Button size="sm" data-testid={`case-report-btn-${c.id}`}>View Joint Report</Button>
                        </Link>
                      )}
                      {!ready && <span className="text-xs text-muted-foreground self-center" data-testid={`case-legacy-note-${c.id}`}>Incomplete — new individual assessments are completed in sacoparentsapp.online.</span>}
                      <Button size="sm" variant="ghost" className="text-destructive" onClick={() => remove(c.id)} data-testid={`case-delete-btn-${c.id}`}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        )}
      </main>
    </div>
  );
}
