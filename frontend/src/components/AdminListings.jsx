import { useEffect, useState } from "react";
import { toast } from "sonner";
import { EyeOff, Eye } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const AdminListings = () => {
  const [rows, setRows] = useState(null);
  const load = () => api.get("/admin/public-listings").then((r) => setRows(r.data)).catch((e) => toast.error(formatApiError(e)));
  useEffect(() => { load(); }, []);

  const toggle = async (p) => {
    const reason = p.hidden ? "" : (window.prompt("Reason for hiding this listing (shown to the professional):", "Bio does not meet neutrality guidelines") ?? null);
    if (reason === null) return;
    try { await api.post(`/admin/public-listings/${p.id}/hide`, { hidden: !p.hidden, reason }); toast.success(p.hidden ? "Listing restored" : "Listing hidden"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  if (!rows) return <p className="text-sm text-muted-foreground">Loading…</p>;
  return (
    <div data-testid="admin-listings">
      <p className="text-sm text-muted-foreground mb-4">Professionals who opted into the public Find a Professional directory. Hide a listing if the bio makes custody recommendations, guarantees, diagnoses or other non-neutral claims.</p>
      {rows.length === 0 && <p className="text-sm text-muted-foreground" data-testid="admin-listings-empty">No professionals are listed yet.</p>}
      <ul className="divide-y divide-border rounded-lg border border-border bg-white">
        {rows.map((p) => (
          <li key={p.id} className={`p-4 flex flex-wrap items-start gap-3 ${p.hidden ? "bg-red-50/40" : ""}`} data-testid={`admin-listing-${p.id}`}>
            <div className="min-w-0 flex-1">
              <p className="font-medium">{p.name}{[p.pro_role, p.organization, p.city, p.zip].filter(Boolean).length > 0 && <span className="text-muted-foreground text-sm"> · {[p.pro_role, p.organization, p.city, p.zip].filter(Boolean).join(" · ")}</span>}</p>
              <p className="text-xs text-muted-foreground">{p.email}{!p.approved && " · NOT APPROVED"}</p>
              {p.bio && <p className="mt-1 text-sm">{p.bio}</p>}
              {p.hidden && <p className="mt-1 text-xs font-medium text-red-700" data-testid={`admin-listing-hidden-${p.id}`}>Hidden: {p.hidden_reason || "no reason given"}</p>}
            </div>
            <Button size="sm" variant={p.hidden ? "default" : "outline"} onClick={() => toggle(p)} data-testid={`admin-listing-toggle-${p.id}`}>
              {p.hidden ? <><Eye className="h-4 w-4" /> Restore</> : <><EyeOff className="h-4 w-4" /> Hide</>}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
};
