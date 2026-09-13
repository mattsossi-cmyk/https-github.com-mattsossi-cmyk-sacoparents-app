import { useEffect, useState } from "react";
import { Mail } from "lucide-react";
import api from "@/lib/api";

const KIND_LABEL = {
  invitation: "Parent invitation", completion_nudge: "Completion nudge", report_ready: "Report ready notice", follow_up_reminder: "Follow-up reminder",
  court_referral: "Court referral", court_referral_declined: "Referral declined", court_submission: "Submission to court", hearing_date: "Hearing date notice",
  hearing_reminder: "Hearing reminder", court_packet: "Court Packet sent", court_packet_code: "Court Packet access code", court_response: "Court response",
};

const mask = (e) => (e && e.includes("@") ? `${e.slice(0, 2)}…@${e.split("@")[1]}` : e || "");

export function CommunicationsLog({ url, title = "Communications Log", compact = false }) {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get(url).then((r) => setItems(r.data)).catch(() => setItems([])); }, [url]);
  return (
    <section className={compact ? "" : "bg-white border border-border rounded-lg p-6"} data-testid="communications-log">
      <h2 className={compact ? "text-sm font-semibold flex items-center gap-2" : "text-lg font-semibold flex items-center gap-2"}><Mail className="h-4 w-4" /> {title}</h2>
      {!compact && <p className="text-xs text-muted-foreground mt-1">Every email, reminder, and court notice sent for this case, in one timeline. Recipient addresses are masked.</p>}
      {items === null ? (
        <p className="mt-3 text-sm text-muted-foreground" data-testid="communications-loading">Loading…</p>
      ) : items.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground" data-testid="communications-empty">Nothing sent yet.</p>
      ) : (
        <ol className="mt-3 space-y-1.5" data-testid="communications-list">
          {items.map((c) => (
            <li key={c.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 rounded-md border border-border px-3 py-2 text-sm" data-testid={`communication-${c.id}`}>
              <span className="text-xs text-muted-foreground tabular-nums">{c.at?.slice(0, 16).replace("T", " ")}</span>
              <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-semibold text-brand-purple">{KIND_LABEL[c.kind] || c.kind}</span>
              <span className="min-w-0 flex-1 truncate">{c.subject}</span>
              <span className="text-xs text-muted-foreground">→ {c.to_role || "Recipient"} {mask(c.to)}</span>
              {c.provider === "skipped" && <span className="text-xs text-amber-700">not delivered (test address)</span>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
