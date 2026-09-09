import { CheckCircle2, XCircle, HelpCircle, Clock, ShieldAlert } from "lucide-react";

const STATUS = {
  pending: { label: "Awaiting the professional's decision", icon: Clock, cls: "text-muted-foreground" },
  prepared: { label: "Accepted — your private assessment invitations were sent", icon: CheckCircle2, cls: "text-align-green" },
  declined: { label: "Declined by the professional", icon: XCircle, cls: "text-red-700" },
  declined_conflict: { label: "Unable to accept due to a conflict of interest", icon: ShieldAlert, cls: "text-red-700" },
  expired: { label: "Invitation expired after 72 hours — you may invite another professional", icon: Clock, cls: "text-align-yellow" },
};

const lastMessage = (r) => [...(r.events || [])].reverse().find((e) => e.by === "professional" && e.note && e.type !== "conflict_reported");

export const ParentRequestStatus = ({ requests }) => {
  if (!requests?.length) return null;
  return (
    <div data-testid="parent-requests-section">
      <h2 className="text-2xl font-semibold mb-1">My Facilitation Requests</h2>
      <p className="text-sm text-muted-foreground mb-4">Status of the professionals you've asked to facilitate a family-violence assessment.</p>
      <div className="grid md:grid-cols-2 gap-4">
        {requests.map((r) => {
          const s = STATUS[r.status] || STATUS.pending;
          const msg = lastMessage(r);
          return (
            <div key={r.id} className="bg-white border border-border rounded-lg p-5" data-testid={`parent-request-${r.id}`}>
              <p className="text-xs uppercase tracking-widest text-red-700 font-semibold">Family Violence Assessment</p>
              <h3 className="text-lg font-semibold mt-1">{r.child_name ? `For ${r.child_name}` : "Joint Assessment"}</h3>
              <p className="text-sm text-muted-foreground mt-1">Professional: {r.professional_name || "—"}</p>
              <p className={`mt-3 flex items-start gap-2 text-sm font-medium ${s.cls}`} data-testid={`parent-request-status-${r.id}`}>
                <s.icon className="h-4 w-4 shrink-0 mt-0.5" /> {s.label}
              </p>
              {msg && (
                <div className="mt-3 bg-secondary/60 border border-border rounded-md p-3 text-sm" data-testid={`parent-request-message-${r.id}`}>
                  <p className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
                    <HelpCircle className="h-3.5 w-3.5" /> {msg.type === "info_requested" ? "The professional asked:" : "Note from the professional:"}
                    <span className="ml-auto font-normal">{String(msg.at).slice(0, 10)}</span>
                  </p>
                  <p className="mt-1">{msg.note}</p>
                  {msg.type === "info_requested" && r.status === "pending" && (
                    <p className="mt-2 text-xs text-muted-foreground">Reply to the professional's email to answer. Your request stays open until it expires.</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
