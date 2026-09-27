import { useEffect, useState } from "react";
import { Mail, RefreshCw, UserPlus } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STATUS = { invited: ["Invited", "bg-align-yellow/20 text-amber-800"], registered: ["Registered · awaiting credentials", "bg-align-blue/15 text-align-blue"], accepted: ["Accepted", "bg-align-green/15 text-align-green"] };
const EMPTY = { name: "", email: "", zip: "", profession: "" };

export function InviteProfessional() {
  const [form, setForm] = useState(EMPTY);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const load = () => api.get("/admin/pro-invites").then((r) => setItems(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const send = async (e) => {
    e.preventDefault(); setBusy(true);
    try { const { data } = await api.post("/admin/pro-invites", form); toast[data.email_sent ? "success" : "error"](data.email_sent ? `Invitation sent to ${data.email}` : `Invitation saved but the email could not be sent${data.email_error ? ` — ${data.email_error}` : ""}. Run the Email health check below.`, { duration: 9000 }); setForm(EMPTY); load(); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };
  const [health, setHealth] = useState(null);
  const [checking, setChecking] = useState(false);
  const runHealth = async () => { setChecking(true); try { const { data } = await api.post("/admin/email-health"); setHealth(data); } catch (err) { toast.error(formatApiError(err)); } finally { setChecking(false); } };
  const resend = async (i) => { try { await api.post(`/admin/pro-invites/${i.id}/resend`); toast.success(`Reminder sent to ${i.email}`); load(); } catch (err) { toast.error(formatApiError(err)); } };
  return (
    <section className="bg-white border border-border rounded-lg p-6" data-testid="invite-professional-section">
      <h2 className="text-lg font-semibold flex items-center gap-2"><UserPlus className="h-5 w-5 text-brand-purple" /> Invite a professional</h2>
      <p className="text-sm text-muted-foreground mt-1">Send a personal registration link. The professional enters their license or credential details; you then review and accept them under <strong>Pending Credentials</strong>.</p>
      <form onSubmit={send} className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5 items-end" data-testid="invite-professional-form">
        <div className="space-y-1"><Label htmlFor="inv-name">Full name</Label><Input id="inv-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="invite-name" /></div>
        <div className="space-y-1"><Label htmlFor="inv-email">Email</Label><Input id="inv-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="invite-email" /></div>
        <div className="space-y-1"><Label htmlFor="inv-zip">Practice ZIP code</Label><Input id="inv-zip" required maxLength={10} placeholder="78205" value={form.zip} onChange={(e) => setForm({ ...form, zip: e.target.value })} data-testid="invite-zip" /></div>
        <div className="space-y-1"><Label htmlFor="inv-prof">Profession (optional)</Label><Input id="inv-prof" placeholder="e.g. Family Law Attorney" value={form.profession} onChange={(e) => setForm({ ...form, profession: e.target.value })} data-testid="invite-profession" /></div>
        <Button type="submit" disabled={busy} data-testid="invite-submit"><Mail className="h-4 w-4 mr-1" /> {busy ? "Sending…" : "Send invitation"}</Button>
      </form>
      <div className="mt-4 rounded-md border border-dashed border-border p-3" data-testid="email-health-panel">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground">Invitations not arriving? Send a test email to <strong>your own address</strong> and see exactly which sender this deployment is using.</p>
          <Button type="button" size="sm" variant="outline" onClick={runHealth} disabled={checking} data-testid="email-health-btn">{checking ? "Checking…" : "Run email health check"}</Button>
        </div>
        {health && (
          <div className="mt-3 text-xs space-y-1" data-testid="email-health-result">
            <p className={`font-semibold ${health.delivered_via === "none" ? "text-red-700" : "text-align-green"}`} data-testid="email-health-status">
              {health.delivered_via === "none" ? "No sender could deliver the test email." : `Test email delivered to ${health.sent_to} via ${health.delivered_via === "resend" ? `your domain sender (${health.config.resend_from})` : "the default Align sender"}.`}
            </p>
            <p>Custom-domain sender (Resend): {health.config.resend_configured ? `configured as ${health.config.resend_from} — ${health.resend.ok ? "OK" : `FAILED (${health.resend.status || "no response"}) ${health.resend.error}`}` : "not configured in this deployment"}</p>
            <p>Default Align sender: {health.config.emergent_email_key ? (health.fallback.attempted ? (health.fallback.ok ? "OK" : `FAILED ${health.fallback.error}`) : "available (not needed)") : "key missing"}</p>
            {health.hints.map((h, i) => <p key={i} className="text-amber-800" data-testid={`email-health-hint-${i}`}>• {h}</p>)}
          </div>
        )}
      </div>
      <h3 className="mt-6 text-sm font-semibold">Invitations ({items.length})</h3>
      {items.length === 0 ? <p className="text-xs text-muted-foreground mt-1" data-testid="invites-empty">No invitations yet.</p> : (
        <ul className="mt-2 divide-y divide-border" data-testid="invites-list">
          {items.map((i) => (
            <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm" data-testid={`invite-${i.id}`}>
              <div><p className="font-medium">{i.name} <span className="text-muted-foreground font-normal">· {i.email}</span></p><p className="text-xs text-muted-foreground">ZIP {i.zip}{i.profession ? ` · ${i.profession}` : ""} · invited {String(i.created_at).slice(0, 10)}{i.invited_by_name ? ` by ${i.invited_by_name}` : ""}</p></div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${(STATUS[i.status] || STATUS.invited)[1]}`} data-testid={`invite-status-${i.id}`}>{(STATUS[i.status] || STATUS.invited)[0]}</span>
                {i.status === "invited" && <Button size="sm" variant="outline" onClick={() => resend(i)} data-testid={`invite-resend-${i.id}`}><RefreshCw className="h-3.5 w-3.5 mr-1" /> Resend</Button>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
