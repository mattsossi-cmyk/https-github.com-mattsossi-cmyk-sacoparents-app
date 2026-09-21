import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import { AdminAddProfessional } from "@/components/AdminAddProfessional";

export function AdminProfessionals() {
  const [pros, setPros] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState("");

  const emailTest = async () => {
    setTesting(true);
    try {
      const { data } = await api.post("/admin/email-test");
      setTestResult(`Provider accepted the message for ${data.to} at ${data.sent_at} — sender: ${data.sender} (id ${data.provider_id || "n/a"}, build ${data.build}). Check inbox and spam.`);
      toast.success("Test email sent");
    } catch (e) { setTestResult(""); toast.error(formatApiError(e)); } finally { setTesting(false); }
  };

  useEffect(() => { api.get("/admin/professionals").then((r) => setPros(r.data)).catch(() => {}); }, []);

  const toggle = async (p) => {
    try {
      const { data } = await api.post(`/admin/verify-credentials/${p.id}`, { verified: !p.credentials_verified });
      toast.success(data.credentials_verified ? "Credentials marked verified" : "Verification removed");
      setPros((prev) => prev.map((x) => (x.id === p.id ? { ...x, credentials_verified: data.credentials_verified } : x)));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const revoke = async (p) => {
    const reason = window.prompt(`Revoke SA CoParents approval for ${p.name}? Enter a brief reason (kept in the declined log):`);
    if (reason === null) return;
    if (!reason.trim()) { toast.error("A brief reason is required"); return; }
    try {
      await api.post(`/admin/revoke-professional/${p.id}`, { reason });
      toast.success(`${p.name} removed from approved professionals`);
      setPros((prev) => prev.filter((x) => x.id !== p.id));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const resend = async (p) => {
    try { await api.post(`/admin/professionals/${p.id}/resend-invite`); toast.success(`Invitation re-sent to ${p.email}`); } catch (e) { toast.error(formatApiError(e)); }
  };

  const needle = q.trim().toLowerCase();
  const shown = pros.filter((p) => !needle || [p.name, p.email, p.profile?.organization, p.profile?.license_number].some((v) => (v || "").toLowerCase().includes(needle)));
  const verifiedCount = pros.filter((p) => p.credentials_verified).length;

  return (
    <section className="bg-white border border-border rounded-lg p-6 mb-6" data-testid="admin-professionals-section">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-lg font-semibold">Approved Professionals <span className="text-sm text-muted-foreground font-normal">({verifiedCount}/{pros.length} credentials verified)</span></h2>
        <div className="flex items-center gap-3">
          <Button size="sm" variant="outline" disabled={testing} onClick={emailTest} data-testid="admin-email-test-btn">{testing ? "Sending…" : "Send me a delivery test email"}</Button>
          <button onClick={() => setOpen((v) => !v)} className="text-sm font-medium text-primary hover:underline" data-testid="admin-professionals-toggle">{open ? "Hide" : "Manage professionals"}</button>
        </div>
      </div>
      {testResult && <p className="mt-2 text-xs text-muted-foreground" data-testid="admin-email-test-result">{testResult}</p>}
      {open && (
        <div className="mt-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, email, organization or license" className="max-w-md" data-testid="admin-professionals-search" />
            <AdminAddProfessional onAdded={(p) => setPros((prev) => [...prev, p].sort((a, b) => a.name.localeCompare(b.name)))} />
          </div>
          <ul className="mt-3 space-y-2" data-testid="admin-professionals-list">
            {shown.length === 0 && <li className="text-sm text-muted-foreground" data-testid="admin-professionals-empty">No approved professionals match.</li>}
            {shown.map((p) => (
              <li key={p.id} className="flex items-start justify-between gap-3 border border-border rounded-md px-4 py-3" data-testid={`approved-pro-${p.id}`}>
                <div className="min-w-0">
                  <p className="text-sm font-medium flex items-center gap-2 flex-wrap">{p.name}{p.profile?.degrees && <span className="text-muted-foreground font-normal">, {p.profile.degrees}</span>} {p.credentials_verified && <VerifiedBadge testId={`approved-pro-verified-${p.id}`} />}{p.invite_pending && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800" data-testid={`approved-pro-invite-pending-${p.id}`}>Invite pending</span>}</p>
                  <p className="text-xs text-muted-foreground">{p.email}{p.profile?.phone ? ` · ${p.profile.phone}` : ""}</p>
                  <p className="text-xs text-muted-foreground mt-1">{[p.profile?.pro_role, p.profile?.organization, p.profile?.license_number ? `License ${p.profile.license_number}` : ""].filter(Boolean).join(" · ") || "No credential details provided"}</p>
                </div>
                <div className="flex flex-col sm:flex-row gap-2 shrink-0">
                  {p.invite_pending && <Button size="sm" variant="outline" onClick={() => resend(p)} data-testid={`resend-invite-btn-${p.id}`}>Resend invite</Button>}
                  <Button size="sm" variant={p.credentials_verified ? "outline" : "default"} onClick={() => toggle(p)} data-testid={`verify-pro-btn-${p.id}`}>
                    {p.credentials_verified ? "Remove verification" : "Mark license verified"}
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => revoke(p)} data-testid={`revoke-pro-btn-${p.id}`}>Revoke approval</Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
