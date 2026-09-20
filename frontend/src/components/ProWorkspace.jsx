import { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { MatterNotes } from "@/components/MatterNotes";
import { SessionOutcome } from "@/components/SessionOutcome";
import { CourtPacketPanel } from "@/components/CourtPacketPanel";
import { ProfessionalStatement } from "@/components/ProfessionalStatement";
import { LegalLensCard } from "@/components/LegalLensCard";
import { CommunicationsLog } from "@/components/CommunicationsLog";

export function ProWorkspace({ rid, steps, outcome, onOutcomeSaved, courtReady }) {
  const [activity, setActivity] = useState(null);

  const load = () => {
    api.get(`/joint/reports/${rid}/activity`).then((r) => setActivity(r.data)).catch(() => {});
  };
  useEffect(load, [rid]);

  return (
    <div className="no-print grid md:grid-cols-2 gap-6 mt-10" data-testid="pro-workspace">
      {steps && <SessionOutcome rid={rid} steps={steps} initial={outcome} onSaved={(o) => { onOutcomeSaved?.(o); load(); }} />}
      {courtReady !== undefined && <LegalLensCard rid={rid} />}
      {courtReady !== undefined && <ProfessionalStatement rid={rid} canSubmit={courtReady} />}
      {courtReady !== undefined && <CourtPacketPanel rid={rid} ready={courtReady} />}
      <section className="bg-white border border-border rounded-lg p-6" data-testid="pro-notes-section">
        <h2 className="text-lg font-semibold" data-testid="pro-notes-heading">Professional Notes</h2>
        <MatterNotes rid={rid} />
      </section>

      <CommunicationsLog url={`/joint/reports/${rid}/communications`} exportHref={`${process.env.REACT_APP_BACKEND_URL}/api/joint/reports/${rid}/communications.pdf`} />

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
        {activity && (activity.lifecycle || []).length > 0 && (
          <div className="mt-6" data-testid="pro-lifecycle">
            <h3 className="text-sm font-semibold">Case lifecycle</h3>
            <ul className="mt-2 space-y-1.5 text-sm" data-testid="pro-lifecycle-list">
              {activity.lifecycle.map((ev, i) => (
                <li key={i} className="border border-border rounded-md px-3 py-2" data-testid={`pro-lifecycle-event-${i}`}>
                  <div className="flex items-center justify-between gap-3">
                    <span><span className="font-medium">{ev.action}</span> <span className="text-muted-foreground">· {ev.by_name || "Unknown"} ({ev.by_role})</span></span>
                    <span className="text-xs text-muted-foreground shrink-0">{String(ev.at).slice(0, 16).replace("T", " ")}</span>
                  </div>
                  {ev.note && <p className="text-xs text-muted-foreground mt-1 italic">“{ev.note}”</p>}
                </li>
              ))}
            </ul>
          </div>
        )}
        {activity && (
          <div className="mt-6" data-testid="pro-access-log">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Report Access Log</h3>
              <span className="text-xs text-muted-foreground" data-testid="pro-access-counts">{activity.view_count || 0} views · {activity.download_count || 0} downloads</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1 mb-3">Who opened or downloaded the report, and when. Downloaded copies cannot be recalled.</p>
            {(activity.access_log || []).length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="pro-access-empty">No one has viewed or downloaded this report yet.</p>
            ) : (
              <ul className="space-y-1.5 text-sm max-h-64 overflow-y-auto pr-1" data-testid="pro-access-list">
                {activity.access_log.map((ev, i) => (
                  <li key={i} className="flex items-center justify-between gap-3 border border-border rounded-md px-3 py-2" data-testid={`pro-access-event-${i}`}>
                    <span className="min-w-0">
                      <span className={`inline-block text-[10px] font-bold uppercase tracking-wider rounded px-1.5 py-0.5 mr-2 ${ev.kind === "download" ? "bg-brand-purple/10 text-brand-purple" : "bg-secondary text-muted-foreground"}`}>{ev.kind === "download" ? "PDF" : "View"}</span>
                      <span className="font-medium">{ev.by_name || "Unknown"}</span>
                      <span className="text-muted-foreground"> · {ev.by_role}</span>
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0">{String(ev.at).slice(0, 16).replace("T", " ")}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
