import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";

export default function AcceptInvite() {
  const [requests, setRequests] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/joint/professional-requests").then((r) => {
      setRequests((Array.isArray(r.data) ? r.data : []).filter((q) => !q.status || q.status === "pending"));
    }).catch((e) => toast.error(formatApiError(e)));
  }, []);

  const accept = async (reqId) => {
    try {
      const { data } = await api.post(`/joint/professional-requests/${reqId}/prepare`);
      toast.success("Invitation accepted — parent invitations sent");
      navigate(`/joint/${data.report_id}`);
    } catch (e) { toast.error(formatApiError(e)); }
  };

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
          Parents invite you through SA CoParents. Accepting an invitation gives you access only to the
          reports specifically authorized by the parent — it does not create a professional relationship
          or grant access to the parent's entire SA CoParents account.
        </p>

        {requests === null ? (
          <p className="text-sm text-muted-foreground mt-10" data-testid="accept-loading">Loading invitations…</p>
        ) : requests.length === 0 ? (
          <div className="mt-10 bg-white border border-border rounded-lg p-8 text-center" data-testid="accept-empty">
            <p className="font-semibold text-lg">No pending parent invitations</p>
            <p className="text-sm text-muted-foreground mt-2">When a parent sends you a secure invitation connected to a family matter, it will appear here. Invitation links are single-use and expire after 72 hours.</p>
          </div>
        ) : (
          <ul className="mt-10 space-y-4" data-testid="accept-list">
            {requests.map((q) => (
              <li key={q.id} className="bg-white border border-border rounded-lg p-6" data-testid={`accept-req-${q.id}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold" data-testid={`accept-parent-${q.id}`}>From: {q.parent_name || q.parent_email}</p>
                    <p className="text-sm text-muted-foreground mt-1">Child: {q.child_name || "—"} {q.co_parent_name ? `· Other parent: ${q.co_parent_name}` : ""}</p>
                    {q.created_at && <p className="text-xs text-muted-foreground mt-1">Sent: {String(q.created_at).slice(0, 10)}</p>}
                  </div>
                  <Button onClick={() => accept(q.id)} className="gap-2 shrink-0" data-testid={`accept-btn-${q.id}`}>
                    <CheckCircle2 className="h-4 w-4" /> Accept Invitation
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
