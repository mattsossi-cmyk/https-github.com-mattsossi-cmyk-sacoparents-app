import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Trash2, CheckCircle2, Circle, Mail, Scale, ShieldAlert, Link2, Unlink } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { CircleNav } from "@/components/CircleNav";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ReminderPreviewButton } from "@/components/ReminderPreview";

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
  const { user, logout } = useAuth();
  const isPro = user?.role === "professional";
  const [pendingPros, setPendingPros] = useState([]);

  useEffect(() => {
    if (user?.role === "admin") {
      api.get("/admin/pending-professionals").then((r) => setPendingPros(r.data)).catch(() => {});
    }
  }, [user]);

  const approvePro = async (id) => {
    try {
      await api.post(`/admin/approve-professional/${id}`);
      toast.success("Professional approved");
      setPendingPros((prev) => prev.filter((p) => p.id !== id));
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

  return (
    <div className="min-h-screen bg-background" data-testid="dashboard-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" data-testid="dash-brand-link">
            <BrandLogo />
          </Link>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground hidden sm:block" data-testid="user-email">{user?.email}</span>
            <Button variant="outline" size="sm" onClick={async () => { await logout(); navigate("/"); }} data-testid="logout-btn">
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 space-y-12">
        <div>
          <h1 className="text-4xl font-semibold" data-testid="dash-heading">Dashboard</h1>
          <p className="text-muted-foreground mt-2" data-testid="dash-subtext">Your individual assessments come from sacoparentsapp.online. Invite your co-parent to explore one issue together.</p>
        </div>

        {isPro && (
          <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="primary-actions-grid">
            <Link to="/accept-invite" className="bg-white border-2 border-primary/40 rounded-lg p-5 hover:border-primary transition-colors" data-testid="action-accept-invite">
              <p className="font-semibold">Accept a Parent Invitation</p>
              <p className="text-xs text-muted-foreground mt-1">Review and accept secure invitations from parents.</p>
            </Link>
            <Link to="/hub" className="bg-white border border-border rounded-lg p-5 hover:border-primary/50 transition-colors" data-testid="action-family-matters">
              <p className="font-semibold">My Family Matters</p>
              <p className="text-xs text-muted-foreground mt-1">Track participation and matter status.</p>
            </Link>
            <Link to="/joint/new" className="bg-white border border-border rounded-lg p-5 hover:border-primary/50 transition-colors" data-testid="action-invite-parents">
              <p className="font-semibold">Invite Parents to Participate</p>
              <p className="text-xs text-muted-foreground mt-1">Create a family matter and invite both parents separately.</p>
            </Link>
            <a href="#joint-reports-list" className="bg-white border border-border rounded-lg p-5 hover:border-primary/50 transition-colors" data-testid="action-joint-reports">
              <p className="font-semibold">Joint Alignment Reports</p>
              <p className="text-xs text-muted-foreground mt-1">Reports ready to generate or review.</p>
            </a>
          </section>
        )}

        {isPro && user?.approved === false && (
          <div className="bg-align-yellow/10 border border-align-yellow/40 rounded-lg p-5 mb-6" data-testid="approval-pending-banner">
            <p className="font-semibold">Your professional account is pending approval</p>
            <p className="text-sm text-muted-foreground mt-1">SA CoParents reviews new professional accounts before they can create Professional Alignment Cases. You'll receive an email once approved.</p>
          </div>
        )}

        {user?.role === "admin" && (
          <section className="bg-white border-2 border-align-yellow/50 rounded-lg p-6 mb-6" data-testid="admin-approvals-section">
            <h2 className="text-lg font-semibold">Pending Professional Approvals</h2>
            {pendingPros.length === 0 ? (
              <p className="text-sm text-muted-foreground mt-2" data-testid="admin-approvals-empty">No professionals awaiting approval.</p>
            ) : (
              <ul className="mt-3 space-y-2" data-testid="admin-approvals-list">
                {pendingPros.map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-3 border border-border rounded-md px-4 py-3" data-testid={`pending-pro-${p.id}`}>
                    <div>
                      <p className="text-sm font-medium">{p.name}</p>
                      <p className="text-xs text-muted-foreground">{p.email}</p>
                    </div>
                    <Button size="sm" onClick={() => approvePro(p.id)} data-testid={`approve-pro-btn-${p.id}`}>Approve</Button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {isPro && (
          <section data-testid="circle-nav-section">
            <CircleNav isPro={isPro} />
          </section>
        )}

        <div className="grid md:grid-cols-2 gap-4" data-testid="tools-grid">
          <div className="bg-white border border-border rounded-lg p-6" data-testid="individual-tools-card">
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
              <div className="flex gap-2" data-testid="ext-link-block">
                <Input value={linkCode} onChange={(e) => setLinkCode(e.target.value.toUpperCase())} placeholder="Link code from sacoparentsapp.online" className="h-11 uppercase tracking-widest" maxLength={8} data-testid="ext-link-code-input" />
                <Button onClick={linkAccount} disabled={linkCode.trim().length !== 8 || busy} className="h-11 gap-1.5" data-testid="ext-link-btn"><Link2 className="h-4 w-4" /> Link</Button>
              </div>
            )}
          </div>
          <div className="bg-white border-2 border-primary/30 rounded-lg p-6" data-testid="joint-tools-card">
            <p className="text-xs uppercase tracking-widest text-primary font-bold">Joint Tools</p>
            {isPro ? (
              <>
                <h2 className="text-2xl font-semibold mt-1">Create a Joint Report</h2>
                <p className="text-sm text-muted-foreground mt-2 mb-5">Compare perspectives. Find alignment. Identify issues that may need discussion.</p>
                <Link to="/joint/new" data-testid="create-joint-report-link">
                  <Button className="gap-2" data-testid="create-joint-report-btn"><Mail className="h-4 w-4" /> Create a Professional Alignment Case</Button>
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
          {isPro && (
          <div className="bg-white border border-border rounded-lg p-6" data-testid="agreement-card">
            <p className="text-xs uppercase tracking-widest text-brand-teal font-bold">Co-Parenting Agreement</p>
            <h2 className="text-2xl font-semibold mt-1">Create a Joint Agreement</h2>
            <p className="text-sm text-muted-foreground mt-2 mb-5">Invite the other parent to create the joint co-parenting agreement — each parent proposes terms privately.</p>
            <Link to="/joint/new?kind=agreement" data-testid="create-agreement-link">
              <Button variant="outline" className="gap-2" data-testid="create-agreement-btn"><Scale className="h-4 w-4" /> Invite Co-Parent to Joint Agreement</Button>
            </Link>
          </div>
          )}
          <div className="bg-white border-2 border-red-200 rounded-lg p-6" data-testid="fv-contact-card">
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
            <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="e.g. SA-EDU-482731" className="h-12 tracking-[0.2em] uppercase font-semibold" maxLength={16} data-testid="invitation-code-input" />
            <Button onClick={acceptCode} disabled={code.trim().length < 6 || busy} className="h-12" data-testid="accept-invitation-btn">Accept</Button>
          </div>
        </div>

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

        <div data-testid="joint-reports-section">
          <h2 className="text-2xl font-semibold mb-4">Joint Reports</h2>
          {joints === null ? (
            <p className="text-muted-foreground" data-testid="joints-loading">Loading…</p>
          ) : joints.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="joints-empty">No joint reports yet. Create one above to invite your co-parent.</p>
          ) : (
            <div className="grid md:grid-cols-2 gap-4" data-testid="joints-grid">
              {joints.map((j) => {
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
                        <Link to={`/joint/${j.id}/assess`} data-testid={`joint-complete-link-${j.id}`}>
                          <Button size="sm" data-testid={`joint-complete-btn-${j.id}`}>Complete My Assessment</Button>
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
          )}
        </div>

        {user?.role === "professional" && (joints || []).some((j) => j.shared_with_me) && (
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

        {user?.role === "professional" && proRequests.length > 0 && (
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
