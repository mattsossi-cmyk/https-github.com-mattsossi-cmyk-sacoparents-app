import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { MatterNotes } from "@/components/MatterNotes";

export function ProWorkspace({ rid }) {
  const [activity, setActivity] = useState(null);

  const load = () => {
    api.get(`/joint/reports/${rid}/activity`).then((r) => setActivity(r.data)).catch(() => {});
  };
  useEffect(load, [rid]);

  return (
    <div className="no-print grid md:grid-cols-2 gap-6 mt-10" data-testid="pro-workspace">
      <section className="bg-white border border-border rounded-lg p-6" data-testid="pro-notes-section">
        <h2 className="text-lg font-semibold" data-testid="pro-notes-heading">Professional Notes</h2>
        <MatterNotes rid={rid} />
      </section>

      <section className="bg-white border border-border rounded-lg p-6" data-testid="pro-activity-section">
        <h2 className="text-lg font-semibold" data-testid="pro-activity-heading">Consent &amp; Activity</h2>
        <p className="text-xs text-muted-foreground mt-1 mb-4">Invitations and access events for this matter.</p>
        {!activity ? (
          <p className="text-sm text-muted-foreground" data-testid="pro-activity-loading">Loading…</p>
        ) : (
          <ul className="space-y-2 text-sm" data-testid="pro-activity-list">
            {(activity.invitations || []).map((inv) => (
              <li key={inv.id} className="flex items-center justify-between border border-border rounded-md px-3 py-2" data-testid={`pro-activity-inv-${inv.role}`}>
                <span>Invitation — {inv.invitee_name || inv.invitee_email}</span>
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{inv.status}</span>
              </li>
            ))}
            {(activity.access_events || []).map((ev, i) => (
              <li key={i} className="flex items-center justify-between border border-border rounded-md px-3 py-2" data-testid={`pro-activity-event-${i}`}>
                <span>{ev.action}</span>
                <span className="text-xs text-muted-foreground">{String(ev.at).slice(0, 16).replace("T", " ")}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
