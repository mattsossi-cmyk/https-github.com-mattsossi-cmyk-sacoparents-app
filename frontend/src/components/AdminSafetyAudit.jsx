import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, Lock } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const AdminSafetyAudit = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/admin/safety-audit").then((r) => setD(r.data)).catch((e) => toast.error(formatApiError(e))); }, []);
  const exportCsv = async () => {
    try {
      const r = await api.get("/admin/safety-audit.csv", { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      Object.assign(document.createElement("a"), { href: url, download: "safety-audit-log.csv" }).click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  if (!d) return null;
  return (
    <div className="mt-8" data-testid="admin-safety-audit">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground"><Lock className="h-4 w-4" /> Safety audit log · {d.total} events (views, pathway decisions, reviews, exports, scan blocks, sign-offs). No answer content.</p>
        <Button size="sm" variant="outline" onClick={exportCsv} data-testid="admin-safety-audit-export-btn"><Download className="h-4 w-4" /> Export CSV</Button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border bg-white">
        <table className="w-full text-sm" data-testid="admin-safety-audit-table">
          <thead className="bg-secondary/50 text-left text-xs uppercase tracking-wide text-muted-foreground"><tr><th className="p-2">When</th><th className="p-2">Case</th><th className="p-2">Kind</th><th className="p-2">Action</th><th className="p-2">By</th></tr></thead>
          <tbody className="divide-y divide-border">{d.rows.slice(0, 50).map((e, i) => <tr key={i}><td className="p-2 text-xs">{e.at?.slice(0, 16).replace("T", " ")}</td><td className="p-2 font-mono text-xs">{(e.report_id || "").slice(0, 8)}</td><td className="p-2 text-xs">{e.kind}</td><td className="p-2 text-xs">{e.action}</td><td className="p-2 text-xs">{e.by_role || e.by_name || "—"}</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  );
};
