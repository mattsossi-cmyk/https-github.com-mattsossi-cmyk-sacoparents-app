import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Radio } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const AdminWebhookCheck = () => {
  const [d, setD] = useState(null);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => api.get("/admin/safety-status-webhook").then((r) => setD(r.data)).catch((e) => toast.error(formatApiError(e)));
  useEffect(() => { load(); }, []);
  const ping = async () => {
    setBusy(true);
    try { const r = await api.post("/admin/safety-status-webhook/test"); setRes(r.data); await load(); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  if (!d) return null;
  return (
    <div className="mt-8 rounded-lg border border-border bg-white p-5" data-testid="admin-webhook-check">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="text-sm">
          <p className="flex items-center gap-1.5 font-semibold"><Radio className="h-4 w-4" /> Safety-status webhook to the parent app</p>
          <p className="mt-1 text-xs text-muted-foreground" data-testid="admin-webhook-state">
            Flag <span className={`font-mono font-semibold ${d.enabled ? "text-green-700" : "text-amber-700"}`}>{d.enabled ? "ON" : "OFF"}</span> · secret {d.secret_configured ? "configured" : <span className="font-semibold text-red-700">missing (ALIGN_WEBHOOK_SECRET)</span>} · target <span className="font-mono">{d.target}</span> · v{d.version}
          </p>
        </div>
        <Button size="sm" onClick={ping} disabled={busy || !d.secret_configured} data-testid="admin-webhook-test-btn">{busy ? "Sending…" : "Send signed test ping"}</Button>
      </div>
      {res && (
        <div className={`mt-3 rounded-md border p-3 text-xs ${res.status === "delivered" ? "border-green-300 bg-green-50" : "border-amber-300 bg-amber-50"}`} data-testid="admin-webhook-result">
          <p className="font-semibold">Result: {res.status}{res.http_status ? ` (HTTP ${res.http_status})` : ""}</p>
          {res.response_snippet && <pre className="mt-1 whitespace-pre-wrap break-all font-mono">{res.response_snippet}</pre>}
          <p className="mt-1 text-muted-foreground">Payload sent (test id, no case data): <span className="font-mono">{JSON.stringify(res.payload)}</span></p>
        </div>
      )}
      {d.recent?.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-muted-foreground" data-testid="admin-webhook-recent">
          {d.recent.slice(0, 5).map((e) => <li key={e.id}>{e.at?.slice(0, 16).replace("T", " ")} · {e.test ? "test" : (e.case_id || "").slice(0, 8)} · {e.safety_mode} · {e.status}{e.last_status ? ` (${e.last_status})` : ""}</li>)}
        </ul>
      )}
    </div>
  );
};
