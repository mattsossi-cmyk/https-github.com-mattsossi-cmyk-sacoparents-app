import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { VerifiedBadge } from "@/components/VerifiedBadge";

export function AdminProfessionals() {
  const [pros, setPros] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => { api.get("/admin/professionals").then((r) => setPros(r.data)).catch(() => {}); }, []);

  const toggle = async (p) => {
    try {
      const { data } = await api.post(`/admin/verify-credentials/${p.id}`, { verified: !p.credentials_verified });
      toast.success(data.credentials_verified ? "Credentials marked verified" : "Verification removed");
      setPros((prev) => prev.map((x) => (x.id === p.id ? { ...x, credentials_verified: data.credentials_verified } : x)));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const needle = q.trim().toLowerCase();
  const shown = pros.filter((p) => !needle || [p.name, p.email, p.profile?.organization, p.profile?.license_number].some((v) => (v || "").toLowerCase().includes(needle)));
  const verifiedCount = pros.filter((p) => p.credentials_verified).length;

  return (
    <section className="bg-white border border-border rounded-lg p-6 mb-6" data-testid="admin-professionals-section">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-lg font-semibold">Approved Professionals <span className="text-sm text-muted-foreground font-normal">({verifiedCount}/{pros.length} credentials verified)</span></h2>
        <button onClick={() => setOpen((v) => !v)} className="text-sm font-medium text-primary hover:underline" data-testid="admin-professionals-toggle">{open ? "Hide" : "Manage credential verification"}</button>
      </div>
      {open && (
        <div className="mt-4">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, email, organization or license" className="max-w-md" data-testid="admin-professionals-search" />
          <ul className="mt-3 space-y-2" data-testid="admin-professionals-list">
            {shown.length === 0 && <li className="text-sm text-muted-foreground" data-testid="admin-professionals-empty">No approved professionals match.</li>}
            {shown.map((p) => (
              <li key={p.id} className="flex items-start justify-between gap-3 border border-border rounded-md px-4 py-3" data-testid={`approved-pro-${p.id}`}>
                <div className="min-w-0">
                  <p className="text-sm font-medium flex items-center gap-2 flex-wrap">{p.name} {p.credentials_verified && <VerifiedBadge testId={`approved-pro-verified-${p.id}`} />}</p>
                  <p className="text-xs text-muted-foreground">{p.email}</p>
                  <p className="text-xs text-muted-foreground mt-1">{[p.profile?.pro_role, p.profile?.organization, p.profile?.license_number ? `License ${p.profile.license_number}` : ""].filter(Boolean).join(" · ") || "No credential details provided"}</p>
                </div>
                <Button size="sm" variant={p.credentials_verified ? "outline" : "default"} onClick={() => toggle(p)} data-testid={`verify-pro-btn-${p.id}`}>
                  {p.credentials_verified ? "Remove verification" : "Mark license verified"}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
