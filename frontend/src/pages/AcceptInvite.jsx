import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, XCircle, HelpCircle, ShieldAlert, Clock } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const hoursLeft = (iso) => Math.max(0, Math.round((new Date(iso) - Date.now()) / 36e5));

function DecisionPanel({ mode, onCancel, onSubmit, busy }) {
  const [text, setText] = useState("");
  const cfg = {
    decline: { title: "Decline this invitation", hint: "Optional brief note to the parent (kept neutral).", cta: "Confirm Decline", required: false },
    info: { title: "Request more information", hint: "What do you need to know before deciding? The parent receives this message.", cta: "Send Question", required: true },
    conflict: { title: "Report a conflict of interest", hint: "Optional private note for your records — the parent is told only that a conflict prevents you from accepting.", cta: "Confirm Conflict", required: false },
  }[mode];
  return (
    <div className="mt-4 border-t border-border pt-4" data-testid={`decision-panel-${mode}`}>
      <p className="font-semibold">{cfg.title}</p>
      <p className="text-xs text-muted-foreground mt-1">{cfg.hint}</p>
      <Textarea value={text} onChange={(e) => setText(e.target.value)} className="mt-3" rows={3} data-testid="decision-text" />
      <div className="mt-3 flex gap-2">
        <Button variant={mode === "info" ? "default" : "destructive"} disabled={busy || (cfg.required && !text.trim())} onClick={() => onSubmit(text)} data-testid="decision-submit-btn">{cfg.cta}</Button>
        <Button variant="ghost" onClick={onCancel} data-testid="decision-cancel-btn">Cancel</Button>
      </div>
    </div>
  );
}

function InviteCard({ q, onDone }) {
  const [mode, setMode] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const act = async (path, reason = "") => {
    setBusy(true);
    try {
      const { data } = await api.post(`/joint/professional-requests/${q.id}/${path}`, { reason });
      if (path === "prepare") { toast.success("Invitation accepted — parent invitations sent"); navigate(`/joint/${data.report_id}`); return; }
      toast.success(path === "request-info" ? "Question sent to the parent" : "Parent notified");
      setMode(null);
      if (path !== "request-info") onDone(q.id, data.status);
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };

  return (
    <li className="bg-white border border-border rounded-lg p-6" data-testid={`accept-req-${q.id}`}>
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="font-semibold" data-testid={`accept-parent-${q.id}`}>From: {q.parent_name || "A parent"}</p>
          <p className="text-sm text-muted-foreground mt-1">Child: {q.child_name || "—"}{q.co_parent_name ? ` · Other parent: ${q.co_parent_name}` : ""}</p>
          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1" data-testid={`accept-expiry-${q.id}`}>
            <Clock className="h-3.5 w-3.5" /> {q.expires_at ? `Expires in ${hoursLeft(q.expires_at)} hours` : "Sent " + String(q.created_at).slice(0, 10)}
          </p>
        </div>
        <Button onClick={() => act("prepare")} disabled={busy} className="gap-2 shrink-0" data-testid={`accept-btn-${q.id}`}>
          <CheckCircle2 className="h-4 w-4" /> Accept Invitation
        </Button>
      </div>
      {!mode && (
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          <Button variant="outline" size="sm" onClick={() => setMode("info")} className="gap-1.5" data-testid={`info-btn-${q.id}`}><HelpCircle className="h-4 w-4" /> Request more information</Button>
          <Button variant="outline" size="sm" onClick={() => setMode("decline")} className="gap-1.5" data-testid={`decline-btn-${q.id}`}><XCircle className="h-4 w-4" /> Decline</Button>
          <Button variant="outline" size="sm" onClick={() => setMode("conflict")} className="gap-1.5 text-red-800 border-red-200" data-testid={`conflict-btn-${q.id}`}><ShieldAlert className="h-4 w-4" /> Conflict of interest</Button>
        </div>
      )}
      {mode && (
        <DecisionPanel mode={mode} busy={busy} onCancel={() => setMode(null)}
          onSubmit={(t) => act(mode === "info" ? "request-info" : mode, t)} />
      )}
    </li>
  );
}

export default function AcceptInvite() {
  const [requests, setRequests] = useState(null);
  const [tokenError, setTokenError] = useState(null);
  const [params] = useSearchParams();
  const token = params.get("token");

  useEffect(() => {
    if (token) {
      api.get("/joint/professional-requests/lookup", { params: { token } })
        .then((r) => setRequests([r.data]))
        .catch((e) => { setTokenError(formatApiError(e)); setRequests([]); });
      return;
    }
    api.get("/joint/professional-requests").then((r) => {
      setRequests((Array.isArray(r.data) ? r.data : []).filter((q) => q.status === "pending"));
    }).catch((e) => toast.error(formatApiError(e)));
  }, [token]);

  const done = (id) => setRequests((rs) => rs.filter((q) => q.id !== id));

  return (
    <div className="min-h-screen bg-background" data-testid="accept-invite-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="accept-back-link">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-4xl font-extrabold text-brand-purple" data-testid="accept-heading">Accept a Parent Invitation</h1>
        <p className="text-muted-foreground mt-3" data-testid="accept-subtext">
          Invitations are single-use, tied to your professional email, and expire after 72 hours. Accepting gives you
          access only to the report the parent authorized — it does not create a professional relationship or grant
          access to the parent's SA CoParents account. Please do not forward invitation links.
        </p>

        {tokenError && (
          <div className="mt-8 bg-red-50 border border-red-200 text-red-900 rounded-lg p-5 text-sm" data-testid="accept-token-error">
            <p className="font-semibold">This invitation link can't be used</p>
            <p className="mt-1">{tokenError}</p>
            <Link to="/accept-invite" className="inline-block mt-3 text-primary font-medium hover:underline" data-testid="accept-view-pending-link">View pending invitations for my account</Link>
          </div>
        )}

        {requests === null ? (
          <p className="text-sm text-muted-foreground mt-10" data-testid="accept-loading">Loading invitations…</p>
        ) : requests.length === 0 && !tokenError ? (
          <div className="mt-10 bg-white border border-border rounded-lg p-8 text-center" data-testid="accept-empty">
            <p className="font-semibold text-lg">No pending parent invitations</p>
            <p className="text-sm text-muted-foreground mt-2">When a parent sends you a secure invitation connected to a family matter, it will appear here.</p>
          </div>
        ) : (
          <ul className="mt-10 space-y-4" data-testid="accept-list">
            {requests.map((q) => <InviteCard key={q.id} q={q} onDone={done} />)}
          </ul>
        )}
      </main>
    </div>
  );
}
