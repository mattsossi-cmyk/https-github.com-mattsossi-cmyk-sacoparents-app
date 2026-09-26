import { useEffect, useState } from "react";
import { History } from "lucide-react";
import api from "@/lib/api";

const fmt = (s) => (s ? String(s).slice(0, 16).replace("T", " ") : "");

export function ProviderHistory({ providerId, refreshKey }) {
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get(`/research/providers/${providerId}/history`).then((r) => setRows(r.data.history)).catch(() => setRows([])); }, [providerId, refreshKey]);
  if (rows === null) return <p className="mt-2 text-xs text-muted-foreground">Loading history…</p>;
  return (
    <div className="mt-2 rounded-md border border-border bg-white p-2 text-xs" data-testid={`provider-history-${providerId}`}>
      <p className="mb-1 flex items-center gap-1 font-semibold text-brand-purple"><History className="h-3.5 w-3.5" /> Freshness history ({rows.length})</p>
      {rows.length === 0 ? <p className="text-muted-foreground" data-testid={`provider-history-empty-${providerId}`}>No checks yet.</p> : (
        <table className="w-full text-left">
          <thead><tr className="text-[10px] uppercase tracking-wide text-muted-foreground"><th className="py-1 pr-2">Checked</th><th className="py-1 pr-2">By</th><th className="py-1 pr-2">Result</th><th className="py-1">Applied</th></tr></thead>
          <tbody>
            {rows.map((h) => (
              <tr key={h.id} className="border-t border-border align-top" data-testid={`provider-history-row-${h.id}`}>
                <td className="py-1 pr-2 whitespace-nowrap">{fmt(h.checked_at)}</td>
                <td className="py-1 pr-2">{h.by_name || "—"}</td>
                <td className="py-1 pr-2">
                  {h.changed?.length ? h.changed.map((k) => <div key={k}><span className="font-semibold text-amber-700 capitalize">{k}</span>: “{h.checks[k].directory || "—"}” → “{h.checks[k].found}”</div>) : <span className="text-align-green font-semibold">all match</span>}
                  {h.not_found?.length > 0 && <div className="text-muted-foreground">not found: {h.not_found.join(", ")}</div>}
                </td>
                <td className="py-1">{h.applied_at ? <span data-testid={`provider-history-applied-${h.id}`}>{fmt(h.applied_at)}{h.applied_by_name ? ` · ${h.applied_by_name}` : ""}<div className="text-muted-foreground">{Object.keys(h.applied || {}).join(", ")}</div></span> : h.changed?.length ? <span className="text-muted-foreground">not applied</span> : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
