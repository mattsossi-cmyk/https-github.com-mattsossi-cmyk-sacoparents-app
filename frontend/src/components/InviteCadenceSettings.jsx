import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Settings2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const InviteCadenceSettings = ({ rid }) => {
  const [d, setD] = useState(null);
  const [days, setDays] = useState("");
  const [max, setMax] = useState(2);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.get(`/joint/reports/${rid}/invite-cadence`).then((r) => { setD(r.data); setDays(r.data.cadence.reminder_days.join(", ")); setMax(r.data.cadence.max_reminders); }).catch(() => setD(null));
  }, [rid]);
  if (!d) return null;
  const save = async () => {
    setBusy(true);
    try {
      const reminder_days = days.split(/[,\s]+/).map((x) => parseInt(x, 10)).filter((n) => Number.isFinite(n));
      const r = await api.put(`/joint/reports/${rid}/invite-cadence`, { reminder_days, max_reminders: Number(max) });
      setD((x) => ({ ...x, cadence: r.data.cadence })); setDays(r.data.cadence.reminder_days.join(", ")); setMax(r.data.cadence.max_reminders);
      toast.success("Reminder settings saved for this case");
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="mt-3 rounded-lg border border-border bg-white p-4" data-testid="invite-cadence-settings">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand-purple"><Settings2 className="h-3.5 w-3.5" /> Invitation reminders (this case)</p>
      <p className="mt-1 text-xs text-muted-foreground">Unopened invitations get up to {d.cadence.max_reminders} automatic reminder{d.cadence.max_reminders === 1 ? "" : "s"} on days {d.cadence.reminder_days.join(" and ") || "—"}; links expire after {d.cadence.expiry_days} days. {d.pending.length} pending.</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_120px_auto] sm:items-end">
        <label className="text-xs">Reminder days (1–{d.cadence.expiry_days - 1}, comma-separated)<Input value={days} onChange={(e) => setDays(e.target.value)} className="mt-1 h-9" data-testid="cadence-days-input" /></label>
        <label className="text-xs">Max reminders (0–2)<Input type="number" min={0} max={2} value={max} onChange={(e) => setMax(e.target.value)} className="mt-1 h-9" data-testid="cadence-max-input" /></label>
        <Button size="sm" onClick={save} disabled={busy} data-testid="cadence-save-btn">Save</Button>
      </div>
    </div>
  );
};
