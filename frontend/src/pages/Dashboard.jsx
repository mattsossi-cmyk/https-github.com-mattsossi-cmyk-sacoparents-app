import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { FileText, Plus, Trash2, CheckCircle2, Circle, Sparkles } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export default function Dashboard() {
  const [cases, setCases] = useState(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const load = () => {
    api.get("/cases")
      .then((r) => setCases(r.data))
      .catch((e) => toast.error(formatApiError(e)));
  };

  useEffect(load, []);

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
          <Link to="/" className="flex items-center gap-2" data-testid="dash-brand-link">
            <FileText className="h-6 w-6 text-primary" />
            <span className="font-display text-2xl font-semibold text-primary">SA CoParents</span>
          </Link>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground hidden sm:block" data-testid="user-email">{user?.email}</span>
            <Button variant="outline" size="sm" onClick={async () => { await logout(); navigate("/"); }} data-testid="logout-btn">
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-semibold" data-testid="dash-heading">Your Assessments</h1>
            <p className="text-muted-foreground mt-2" data-testid="dash-subtext">
              Both parents complete the same assessment. The Joint Alignment Report combines their perspectives.
            </p>
          </div>
          <Link to="/new" data-testid="new-assessment-link">
            <Button className="gap-2" data-testid="new-assessment-btn"><Plus className="h-4 w-4" /> New Joint Assessment</Button>
          </Link>
        </div>

        {cases === null ? (
          <p className="text-muted-foreground" data-testid="cases-loading">Loading…</p>
        ) : cases.length === 0 ? (
          <div className="bg-white border border-dashed border-border rounded-lg p-16 text-center" data-testid="cases-empty">
            <FileText className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
            <p className="text-lg font-medium">No assessments yet</p>
            <p className="text-sm text-muted-foreground mt-1 mb-6">Create your first joint assessment to generate a 10-page Joint Alignment Report.</p>
            <Link to="/new" data-testid="empty-new-link">
              <Button data-testid="empty-new-btn">Create assessment</Button>
            </Link>
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
      </main>
    </div>
  );
}
