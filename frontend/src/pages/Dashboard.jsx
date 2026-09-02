import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { FileText, Plus, Trash2, CheckCircle2, Circle, Sparkles, Mail } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function Dashboard() {
  const [cases, setCases] = useState(null);
  const [joints, setJoints] = useState(null);
  const [connections, setConnections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const load = () => {
    api.get("/cases").then((r) => setCases(r.data)).catch((e) => toast.error(formatApiError(e)));
    api.get("/joint/reports").then((r) => setJoints(r.data)).catch(() => setJoints([]));
    api.get("/joint/connections").then((r) => setConnections(r.data)).catch(() => {});
    api.get("/joint/config").then((r) => setSubjects(r.data.subjects)).catch(() => {});
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

  const remove = async (id) => {
    try {
      await api.delete(`/cases/${id}`);
      toast.success("Assessment deleted");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const loadDemo = async (id) => {
    try {
      await api.post(`/cases/${id}/demo`);
      navigate(`/report/${id}`);
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
          <p className="text-muted-foreground mt-2" data-testid="dash-subtext">Reflect privately, or invite your co-parent to explore one issue together.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-4" data-testid="tools-grid">
          <div className="bg-white border border-border rounded-lg p-6" data-testid="individual-tools-card">
            <p className="text-xs uppercase tracking-widest text-brand-teal font-bold">Individual Tools</p>
            <h2 className="text-2xl font-semibold mt-1">Start a Private Assessment</h2>
            <p className="text-sm text-muted-foreground mt-2 mb-5">Reflect privately on your parenting situation with a structured 10-topic assessment.</p>
            <Link to="/new" data-testid="new-assessment-link">
              <Button variant="outline" className="gap-2" data-testid="new-assessment-btn"><Plus className="h-4 w-4" /> Start a Private Assessment</Button>
            </Link>
          </div>
          <div className="bg-white border-2 border-primary/30 rounded-lg p-6" data-testid="joint-tools-card">
            <p className="text-xs uppercase tracking-widest text-primary font-bold">Joint Tools</p>
            <h2 className="text-2xl font-semibold mt-1">Create a Joint Report</h2>
            <p className="text-sm text-muted-foreground mt-2 mb-5">Compare perspectives. Find alignment. Identify issues that may need discussion.</p>
            <Link to="/joint/new" data-testid="create-joint-report-link">
              <Button className="gap-2" data-testid="create-joint-report-btn"><Mail className="h-4 w-4" /> Invite My Co-Parent</Button>
            </Link>
          </div>
        </div>

        <div className="bg-white border border-border rounded-lg p-6" data-testid="enter-code-card">
          <p className="font-semibold mb-1">Already invited?</p>
          <p className="text-sm text-muted-foreground mb-4">Enter the invitation code from your email to join a Joint Report.</p>
          <div className="flex gap-2 max-w-md">
            <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="e.g. K7P2QX" className="h-12 tracking-[0.3em] uppercase font-semibold" maxLength={6} data-testid="invitation-code-input" />
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
                    <div className="mt-4 space-y-2 text-sm">
                      {rows.map(([label, p]) => (
                        <div key={label} className="flex items-center gap-2" data-testid={`joint-row-${j.id}-${label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
                          {p.completed ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                          <span>{label}: {p.completed ? (p.imported ? "Complete (imported)" : "Complete") : p.accepted ? "In progress" : "Invitation sent"}</span>
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
                          <Button size="sm" variant={ready ? "default" : "secondary"} data-testid={`joint-view-btn-${j.id}`}>{ready ? "View Joint Report" : "View Status"}</Button>
                        </Link>
                      )}
                      {j.is_creator && j.invitation && j.invitation.status === "pending" && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => resend(j.invitation.id)} data-testid={`joint-resend-btn-${j.id}`}>Resend Invitation</Button>
                          <select
                            className="h-9 rounded-md border border-input bg-white px-2 text-sm"
                            value={j.subject}
                            onChange={(e) => changeSubject(j.invitation.id, e.target.value)}
                            data-testid={`joint-change-subject-${j.id}`}
                          >
                            {subjects.map((s) => (
                              <option key={s.key} value={s.key}>{s.label}</option>
                            ))}
                          </select>
                          <Button size="sm" variant="ghost" className="text-destructive" onClick={() => cancelInv(j.invitation.id)} data-testid={`joint-cancel-btn-${j.id}`}>Cancel Invitation</Button>
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

        <div data-testid="assessments-section">
          <h2 className="text-2xl font-semibold mb-4">Private Assessments</h2>
          {cases === null ? (
            <p className="text-muted-foreground" data-testid="cases-loading">Loading…</p>
          ) : cases.length === 0 ? (
            <div className="bg-white border border-dashed border-border rounded-lg p-10 text-center" data-testid="cases-empty">
              <FileText className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">No private assessments yet</p>
              <p className="text-sm text-muted-foreground mt-1">Start one above, or generate a 10-page Joint Alignment Report from one.</p>
            </div>
          ) : (
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
                      {ready ? (
                        <Link to={`/report/${c.id}`} data-testid={`case-report-link-${c.id}`}>
                          <Button size="sm" data-testid={`case-report-btn-${c.id}`}>View Joint Report</Button>
                        </Link>
                      ) : (
                        <Link to={`/new?case=${c.id}`} data-testid={`case-continue-link-${c.id}`}>
                          <Button size="sm" variant="secondary" data-testid={`case-continue-btn-${c.id}`}>Continue</Button>
                        </Link>
                      )}
                      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => loadDemo(c.id)} data-testid={`case-demo-btn-${c.id}`}>
                        <Sparkles className="h-3.5 w-3.5" /> Demo data
                      </Button>
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
      </main>
    </div>
  );
}
