import { useEffect, useState } from "react";
import { Smartphone } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function UrgentSmsSettings() {
  const [s, setS] = useState(null);
  const [mobile, setMobile] = useState("");
  const [on, setOn] = useState(true);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => { api.get("/court-dashboard/alert-settings").then((r) => { setS(r.data); setMobile(r.data.mobile || ""); setOn(r.data.sms_urgent_alerts !== false); }).catch(() => setS({ configured: false })); }, []);
  const save = async () => {
    setBusy(true);
    try { const { data } = await api.put("/court-dashboard/alert-settings", { mobile, sms_urgent_alerts: on }); setS(data); setMobile(data.mobile || ""); toast.success(data.mobile ? "Mobile number saved" : "Text alerts turned off"); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const test = async () => { try { await api.post("/court-dashboard/alert-settings/test-sms"); toast.success("Test text sent"); } catch (e) { toast.error(formatApiError(e)); } };
  if (!s) return null;
  return (
    <section className="mb-6 rounded-lg border border-border bg-white p-4" data-testid="judge-sms-settings">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-bold text-brand-purple"><Smartphone className="h-4 w-4" /> Urgent safety alerts by text
          {s.mobile && s.sms_urgent_alerts !== false ? <span className="rounded-full bg-align-green/15 px-2 py-0.5 text-[10px] font-semibold text-align-green" data-testid="judge-sms-status-on">ON · {s.mobile}</span> : <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground" data-testid="judge-sms-status-off">email only</span>}
        </p>
        <Button size="sm" variant="ghost" onClick={() => setOpen((v) => !v)} data-testid="judge-sms-toggle">{open ? "Close" : "Manage"}</Button>
      </div>
      {open && (
        <div className="mt-3 space-y-3 text-sm">
          <p className="text-xs text-muted-foreground">You always receive urgent-safety alerts by email at {s.email}. Add a mobile number to also get an immediate text. Texts contain only the cause number and a portal link — never message content.</p>
          {!s.configured && <p className="rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs text-amber-800" data-testid="judge-sms-unconfigured">Text delivery is not yet enabled by the administrator; your number will be saved and used as soon as it is.</p>}
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs">Mobile number<input value={mobile} onChange={(e) => setMobile(e.target.value)} placeholder="+1 210 555 0123" className="mt-1 block h-9 w-52 rounded-md border border-input px-2 text-sm" data-testid="judge-sms-mobile" /></label>
            <label className="flex items-center gap-2 text-xs pb-2"><input type="checkbox" checked={on} onChange={(e) => setOn(e.target.checked)} data-testid="judge-sms-enabled" /> Send urgent-safety texts</label>
            <Button size="sm" onClick={save} disabled={busy} data-testid="judge-sms-save">{busy ? "Saving…" : "Save"}</Button>
            {s.mobile && <Button size="sm" variant="outline" onClick={test} disabled={!s.configured} data-testid="judge-sms-test">Send test text</Button>}
          </div>
        </div>
      )}
    </section>
  );
}
