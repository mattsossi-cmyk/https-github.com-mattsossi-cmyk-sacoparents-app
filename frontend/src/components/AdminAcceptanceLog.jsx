import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, CheckCircle2, Circle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

export const AdminAcceptanceLog = ({ endpoint = "/admin/privacy-notice/acceptances", filename = "privacy-notice-acceptances.csv", label = "notice", testId = "admin-acceptance-log" }) => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get(endpoint).then((r) => setD(r.data)).catch((e) => toast.error(formatApiError(e))); }, [endpoint]);

  const exportCsv = async () => {
    try {
      const r = await api.get(`${endpoint}.csv`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = Object.assign(document.createElement("a"), { href: url, download: filename });
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!d) return <p className="text-sm text-muted-foreground">Loading…</p>;
  return (
    <div data-testid={testId}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground" data-testid={`${testId}-summary`}>
          Current {label} version <span className="font-mono font-semibold text-foreground">{d.current_version}</span> · {d.accepted_current} of {d.total} accounts have accepted the current version.
        </p>
        <Button size="sm" variant="outline" onClick={exportCsv} data-testid={`${testId}-export-btn`}><Download className="h-4 w-4" /> Export CSV</Button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border bg-white">
        <table className="w-full text-sm" data-testid={`${testId}-table`}>
          <thead className="bg-secondary/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr><th className="p-3">Account</th><th className="p-3">Role</th><th className="p-3">Accepted version</th><th className="p-3">Accepted at</th><th className="p-3">Status</th></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {d.rows.map((x) => (
              <tr key={x.id} data-testid={`${testId}-row-${x.id}`}>
                <td className="p-3"><p className="font-medium">{x.name || "—"}</p><p className="text-xs text-muted-foreground">{x.email}</p></td>
                <td className="p-3 capitalize">{x.role}</td>
                <td className="p-3 font-mono text-xs">{x.accepted_version || "—"}</td>
                <td className="p-3 text-xs">{fmt(x.accepted_at)}</td>
                <td className="p-3">
                  {x.current
                    ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700"><CheckCircle2 className="h-4 w-4" /> Current</span>
                    : <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-700"><Circle className="h-4 w-4" /> {x.accepted_version ? "Outdated" : "Not accepted"}</span>}
                  {x.history.length > 1 && <p className="mt-1 text-[11px] text-muted-foreground">{x.history.length} acceptances on record</p>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
