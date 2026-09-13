import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Gavel } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function AdminJudges() {
  const [judges, setJudges] = useState([]);
  const [invites, setInvites] = useState([]);
  const [inv, setInv] = useState({ name: "", email: "", court_name: "" });
  const [sending, setSending] = useState(false);
  const load = () => {
    api.get("/admin/judges").then((r) => setJudges(r.data)).catch(() => {});
    api.get("/admin/judges/invites").then((r) => setInvites(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const invite = async () => {
    setSending(true);
    try { await api.post("/admin/judges/invite", inv); toast.success(`Invitation sent to ${inv.email}`); setInv({ name: "", email: "", court_name: "" }); load(); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setSending(false); }
  };

  const approve = async (j) => {
    try { await api.post(`/admin/judges/${j.id}/approve`); toast.success(`${j.name} approved — court account active`); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const decline = async (j) => {
    const reason = window.prompt(`Decline the court account for ${j.name}? Enter a brief reason:`);
    if (reason === null) return;
    if (!reason.trim()) { toast.error("A brief reason is required"); return; }
    try { await api.post(`/admin/judges/${j.id}/decline`, { reason }); toast.success("Court account declined"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const pending = judges.filter((j) => !j.approved);
  const approved = judges.filter((j) => j.approved);
  return (
    <section className="bg-white border border-border rounded-lg p-6 mb-6" data-testid="admin-judges-section">
      <h2 className="text-lg font-semibold flex items-center gap-2"><Gavel className="h-4 w-4" /> Court Accounts <span className="text-sm text-muted-foreground font-normal">({pending.length} pending · {approved.length} approved)</span></h2>
      <p className="text-sm text-muted-foreground mt-1">Judges and court staff who registered. Approve only after confirming the court email and role. Approved accounts see every Court Packet addressed to their email.</p>
      <div className="mt-4 rounded-md border border-brand-purple/30 bg-brand-purple/5 p-4" data-testid="admin-judge-invite-box">
        <p className="text-sm font-medium">Invite a judge or court coordinator</p>
        <p className="text-xs text-muted-foreground">They receive an email link; registering with that address activates the account immediately.</p>
        <div className="mt-2 grid sm:grid-cols-3 gap-2">
          <Input placeholder="Name" value={inv.name} onChange={(e) => setInv({ ...inv, name: e.target.value })} className="h-9" data-testid="judge-invite-name" />
          <Input placeholder="Court email" type="email" value={inv.email} onChange={(e) => setInv({ ...inv, email: e.target.value })} className="h-9" data-testid="judge-invite-email" />
          <Input placeholder="Court (e.g. 285th District Court)" value={inv.court_name} onChange={(e) => setInv({ ...inv, court_name: e.target.value })} className="h-9" data-testid="judge-invite-court" />
        </div>
        <Button size="sm" className="mt-2" onClick={invite} disabled={sending || !inv.name || !inv.email} data-testid="judge-invite-send-btn">{sending ? "Sending…" : "Send court invitation"}</Button>
        {invites.length > 0 && (
          <ul className="mt-3 space-y-1 text-xs" data-testid="admin-judge-invites-list">
            {invites.map((x) => <li key={x.id} className="flex justify-between gap-2" data-testid={`judge-invite-${x.id}`}><span>{x.name} · {x.email}{x.court_name ? ` · ${x.court_name}` : ""}</span><span className={`font-semibold ${x.status === "registered" ? "text-green-800" : "text-muted-foreground"}`}>{x.status === "registered" ? "Registered & active" : `Invited ${x.created_at?.slice(0, 10)}`}</span></li>)}
          </ul>
        )}
      </div>
      {judges.length === 0 && <p className="mt-3 text-sm text-muted-foreground" data-testid="admin-judges-empty">No court accounts yet.</p>}
      <ul className="mt-3 space-y-2" data-testid="admin-judges-list">
        {[...pending, ...approved].map((j) => (
          <li key={j.id} className="flex items-start justify-between gap-3 border border-border rounded-md px-4 py-3" data-testid={`admin-judge-${j.id}`}>
            <div className="min-w-0">
              <p className="text-sm font-medium">{j.name} {j.approved ? <span className="ml-1 rounded-full bg-align-green/15 px-2 py-0.5 text-[11px] font-semibold text-green-900">Approved</span> : <span className="ml-1 rounded-full bg-align-yellow/30 px-2 py-0.5 text-[11px] font-semibold text-yellow-900">Pending</span>}</p>
              <p className="text-xs text-muted-foreground">{j.email}</p>
              <p className="text-xs text-muted-foreground mt-1">{[j.profile?.pro_role, j.profile?.organization, [j.profile?.city, j.profile?.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ") || "No court details provided"}</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2 shrink-0">
              {!j.approved && <Button size="sm" onClick={() => approve(j)} data-testid={`approve-judge-btn-${j.id}`}>Approve</Button>}
              <Button size="sm" variant={j.approved ? "destructive" : "outline"} onClick={() => decline(j)} data-testid={`decline-judge-btn-${j.id}`}>{j.approved ? "Revoke" : "Decline"}</Button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
