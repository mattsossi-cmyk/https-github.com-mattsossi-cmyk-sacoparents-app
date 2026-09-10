import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Inbox, Send, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const STATUS_CLS = { pending: "bg-align-yellow/20 text-yellow-900", accepted: "bg-align-green/15 text-green-900", declined: "bg-secondary text-muted-foreground" };

function ReferralRow({ r, mine, onRespond }) {
  const who = mine ? `To ${r.to_name || "colleague"}` : `From ${r.from_name || "colleague"}`;
  return (
    <li className="border border-border rounded-lg p-4 min-w-0" data-testid={`referral-${r.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">{who}{r.case_code && <span className="text-muted-foreground font-normal"> · Case {r.case_code}</span>}</p>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${STATUS_CLS[r.status] || STATUS_CLS.pending}`} data-testid={`referral-status-${r.id}`}>{r.status}</span>
      </div>
      {r.message && <p className="text-sm text-muted-foreground mt-2 break-words">“{r.message}”</p>}
      {r.response_note && <p className="text-xs text-muted-foreground mt-2 italic">Response: {r.response_note}</p>}
      <p className="text-xs text-muted-foreground mt-2">{String(r.at).slice(0, 10)}</p>
      {!mine && r.status === "pending" && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" className="gap-1.5" onClick={() => onRespond(r, true)} data-testid={`referral-accept-${r.id}`}><CheckCircle2 className="h-3.5 w-3.5" /> Accept</Button>
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => onRespond(r, false)} data-testid={`referral-decline-${r.id}`}><XCircle className="h-3.5 w-3.5" /> Decline</Button>
        </div>
      )}
    </li>
  );
}

export const ReferralInbox = () => {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("received");
  const load = () => api.get("/professionals/referrals").then((r) => setData(r.data)).catch(() => setData({ received: [], sent: [] }));
  useEffect(() => { load(); }, []);
  if (!data || (data.received.length === 0 && data.sent.length === 0)) return null;

  const respond = async (r, accept) => {
    const note = window.prompt(accept ? "Optional note to the referring professional:" : "Optional reason (sent to the referring professional):");
    if (note === null) return;
    try {
      await api.post(`/professionals/referrals/${r.id}/respond`, { accept, note });
      toast.success(accept ? "Referral accepted" : "Referral declined");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const list = data[tab];
  const pending = data.received.filter((r) => r.status === "pending").length;
  return (
    <section className="bg-white border border-border rounded-lg p-6" data-testid="referral-inbox">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold flex items-center gap-2"><Inbox className="h-5 w-5 text-brand-purple" /> Case Referrals {pending > 0 && <span className="text-xs font-bold bg-brand-purple text-white rounded-full px-2 py-0.5" data-testid="referral-pending-count">{pending} new</span>}</h2>
        <div className="flex gap-1" data-testid="referral-tabs">
          <button type="button" onClick={() => setTab("received")} className={`px-3 py-1.5 rounded-md text-sm font-medium ${tab === "received" ? "bg-brand-purple text-white" : "hover:bg-muted"}`} data-testid="referral-tab-received"><Inbox className="inline h-3.5 w-3.5 mr-1" />Received ({data.received.length})</button>
          <button type="button" onClick={() => setTab("sent")} className={`px-3 py-1.5 rounded-md text-sm font-medium ${tab === "sent" ? "bg-brand-purple text-white" : "hover:bg-muted"}`} data-testid="referral-tab-sent"><Send className="inline h-3.5 w-3.5 mr-1" />Sent ({data.sent.length})</button>
        </div>
      </div>
      {list.length === 0 ? (
        <p className="text-sm text-muted-foreground mt-4" data-testid="referral-empty">Nothing here yet. <Link to="/professionals" className="text-primary hover:underline">Open the directory</Link> to refer a case.</p>
      ) : (
        <ul className="mt-4 space-y-3" data-testid={`referral-list-${tab}`}>{list.map((r) => <ReferralRow key={r.id} r={r} mine={tab === "sent"} onRespond={respond} />)}</ul>
      )}
    </section>
  );
};
