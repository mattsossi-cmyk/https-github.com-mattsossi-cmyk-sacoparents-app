import { useEffect, useState } from "react";
import { toast } from "sonner";
import { MessageSquare, Send } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function CourtThread({ baseUrl, side, disabled = false }) {
  const [data, setData] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => api.get(`${baseUrl}/messages`).then((r) => setData(r.data)).catch(() => setData({ messages: [], summary: null }));
  useEffect(() => { load(); }, [baseUrl]);
  const send = async () => {
    setBusy(true);
    try {
      const { data: d } = await api.post(`${baseUrl}/messages`, { text });
      setData((x) => ({ messages: [...(x?.messages || []), d.message], summary: d.summary })); setText(""); toast.success("Message sent");
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const msgs = data?.messages || [];
  return (
    <section className="rounded-lg border border-border bg-white p-5" data-testid="court-thread">
      <h3 className="text-sm font-semibold flex items-center gap-2"><MessageSquare className="h-4 w-4" /> Court–Professional Communication</h3>
      <p className="text-xs text-muted-foreground mt-0.5">Case-specific. Between the court and the assigned professional only — parents are never part of this thread.</p>
      {data?.summary && (
        <div className="mt-3 rounded-md border border-brand-purple/20 bg-brand-purple/5 p-3 text-sm" data-testid="court-thread-summary">
          <p className="text-[11px] font-bold uppercase tracking-widest text-brand-purple">Communication Summary</p>
          <p className="mt-1 leading-relaxed">{data.summary.summary}</p>
          {data.summary.outstanding && <p className="mt-1 text-xs font-semibold text-align-blue">Outstanding: {data.summary.outstanding}</p>}
          <p className="mt-1 text-[11px] text-muted-foreground">{data.summary.disclaimer}</p>
        </div>
      )}
      <ul className="mt-3 space-y-2 max-h-72 overflow-y-auto" data-testid="court-thread-list">
        {data === null ? <li className="text-sm text-muted-foreground">Loading…</li> : msgs.length === 0 ? <li className="text-sm text-muted-foreground" data-testid="court-thread-empty">No messages yet.</li> : msgs.map((m) => (
          <li key={m.id} className={`rounded-md px-3 py-2 text-sm ${m.triage?.category === "urgent_safety" ? "border-l-4 border-red-600 " : ""}${m.from_role === side ? "bg-secondary/60 ml-8" : "bg-muted/40 mr-8"}`} data-testid={`court-msg-${m.id}`}>
            <p className="text-[11px] text-muted-foreground"><span className="font-semibold text-foreground">{m.from_role === "court" ? "Court" : "Professional"} · {m.from_name}</span> · {m.at?.slice(0, 16).replace("T", " ")}{m.triage && <span className={`ml-2 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${m.triage.category === "urgent_safety" ? "bg-red-600 text-white" : m.triage.category === "scheduling" ? "bg-align-blue/15 text-align-blue" : "bg-muted text-muted-foreground"}`} data-testid={`court-msg-triage-${m.id}`}>{m.triage.category === "urgent_safety" ? "Urgent · safety" : m.triage.category}</span>}{m.urgent_alert_sent_at && <span className="ml-1 text-[10px] text-red-700" data-testid={`court-msg-urgent-emailed-${m.id}`}>· judge emailed{m.urgent_sms_sent_at ? " + texted" : ""} immediately</span>}</p>
            <p className="mt-0.5 whitespace-pre-wrap leading-relaxed">{m.text}</p>
          </li>
        ))}
      </ul>
      {!disabled && (
        <div className="mt-3 flex gap-2 items-end">
          <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={side === "court" ? "e.g. Please provide an updated status concerning completion of the educational assessments." : "e.g. Both parents have completed their assessments. The Joint Report is being prepared."} className="min-h-[60px]" data-testid="court-thread-input" />
          <Button onClick={send} disabled={busy || !text.trim()} className="bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="court-thread-send-btn"><Send className="h-4 w-4 mr-1" /> Send</Button>
        </div>
      )}
    </section>
  );
}
