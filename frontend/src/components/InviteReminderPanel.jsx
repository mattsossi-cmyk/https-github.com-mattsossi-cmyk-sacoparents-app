import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Mail, RefreshCw } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const day = (iso) => (iso ? new Date(iso).toLocaleDateString() : "—");

export const InviteReminderPanel = () => {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState("");
  const load = () => api.get("/professional/invitations").then((r) => setD(r.data)).catch(() => setD({ invitations: [], count: 0 }));
  useEffect(() => { load(); }, []);
  const reissue = async (inv) => {
    setBusy(inv.id);
    try { await api.post(`/joint/invitations/${inv.id}/reissue`); toast.success(`Fresh link sent to ${inv.invitee_email}`); await load(); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(""); }
  };
  if (!d || d.count === 0) return null;
  return (
    <section className="bg-white border border-border rounded-lg p-6 mb-6" data-testid="invite-reminder-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-widest text-primary font-bold">Unopened invitations</p>
          <p className="text-sm text-muted-foreground mt-1">{d.count} invitation{d.count === 1 ? "" : "s"} not yet accepted. Reminders go out automatically on your cadence; a fresh link resets the 7-day window.</p>
        </div>
      </div>
      <ul className="mt-4 divide-y divide-border" data-testid="invite-reminder-list">
        {d.invitations.map((inv) => (
          <li key={inv.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between" data-testid={`invite-reminder-${inv.id}`}>
            <div className="min-w-0 text-sm">
              <p className="font-medium"><Link to={`/joint/${inv.case_id}`} className="hover:underline" data-testid={`invite-reminder-case-${inv.id}`}>Case {inv.case_code}</Link> · {inv.parent_label}{inv.invitee_name ? ` (${inv.invitee_name})` : ""}</p>
              <p className="text-xs text-muted-foreground">{inv.invitee_email} · sent {day(inv.sent_at)} · reminders {inv.reminders_sent}/{inv.max_reminders}</p>
              <p className="text-xs" data-testid={`invite-reminder-next-${inv.id}`}>
                {inv.expired ? <span className="font-semibold text-red-700">Link expired {day(inv.expires_at)}</span>
                  : inv.next_reminder_at ? <>Next reminder {day(inv.next_reminder_at)} · expires {day(inv.expires_at)}</>
                    : <>No further reminders · expires {day(inv.expires_at)}</>}
              </p>
            </div>
            {inv.can_reissue && <Button size="sm" variant="outline" disabled={busy === inv.id} onClick={() => reissue(inv)} data-testid={`invite-reissue-${inv.id}`}>{busy === inv.id ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />} Send fresh link</Button>}
          </li>
        ))}
      </ul>
    </section>
  );
};
