import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Gavel, Download, RefreshCw, Ban } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const STATUS = {
  sent: ["Sent · not yet opened", "bg-secondary text-muted-foreground"],
  opened: ["Opened by court", "bg-align-blue/15 text-align-blue"],
  acknowledged: ["Receipt acknowledged", "bg-align-green/15 text-green-900"],
  clarification_requested: ["Clarification requested", "bg-align-yellow/25 text-yellow-900"],
  revoked: ["Revoked", "bg-red-50 text-red-700"],
};

const EMPTY = { judge_name: "", judge_email: "", court_name: "", cause_number: "", cover_letter: "" };

export function CourtPacketPanel({ rid, ready }) {
  const [opts, setOpts] = useState(null);
  const [packets, setPackets] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [extra, setExtra] = useState([]);
  const [incOutcome, setIncOutcome] = useState(true);
  const [incClosing, setIncClosing] = useState(true);
  const [attest, setAttest] = useState(false);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.get(`/joint/reports/${rid}/court-packets`).then((r) => setPackets(r.data)).catch(() => {});
    api.get(`/joint/reports/${rid}/court-packets/options`).then((r) => setOpts(r.data)).catch(() => {});
  };
  useEffect(load, [rid]);

  const send = async () => {
    setBusy(true);
    try {
      await api.post(`/joint/reports/${rid}/court-packets`, { ...form, report_ids: extra, include_session_outcome: incOutcome, include_closing_summary: incClosing, attest });
      toast.success(`Court Packet sent to ${form.judge_name} — link and access code emailed separately`);
      setForm(EMPTY); setExtra([]); setAttest(false); setOpen(false); load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };
  const act = async (pid, what) => {
    try { await api.post(`/court-packets/${pid}/${what}`); toast.success(what === "revoke" ? "Court access revoked" : "Packet re-sent with a new link and code"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const others = (opts?.reports || []).filter((o) => !o.primary);
  return (
    <section className="bg-white border border-border rounded-lg p-6 md:col-span-2" data-testid="court-packet-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2"><Gavel className="h-4 w-4" /> Court Packets</h2>
          <p className="text-sm text-muted-foreground mt-1">Send this report, with your cover letter, to a judge. One-time link + access code, read-only, every opening logged, expires in 30 days.</p>
        </div>
        {ready && !open && <Button size="sm" onClick={() => setOpen(true)} data-testid="court-packet-new-btn">Prepare Court Packet</Button>}
      </div>
      {!ready && <p className="mt-3 text-sm text-muted-foreground" data-testid="court-packet-not-ready">Available once both parents have completed and the Joint Report is ready.</p>}

      {open && (
        <div className="mt-5 grid gap-4" data-testid="court-packet-form">
          <div className="grid sm:grid-cols-2 gap-3">
            <Input placeholder="Judge's name (e.g. Judge Maria Lopez)" value={form.judge_name} onChange={(e) => setForm({ ...form, judge_name: e.target.value })} data-testid="court-judge-name" />
            <Input type="email" placeholder="Judge / court coordinator email" value={form.judge_email} onChange={(e) => setForm({ ...form, judge_email: e.target.value })} data-testid="court-judge-email" />
            <Input placeholder="Court (e.g. 285th District Court, Bexar County)" value={form.court_name} onChange={(e) => setForm({ ...form, court_name: e.target.value })} data-testid="court-name" />
            <Input placeholder="Cause number" value={form.cause_number} onChange={(e) => setForm({ ...form, cause_number: e.target.value })} data-testid="court-cause-number" />
          </div>
          <Textarea placeholder="Cover letter to the court. Describe your role, the process the parents completed, and what the enclosed report(s) show. Keep it neutral — no custody recommendations." value={form.cover_letter} onChange={(e) => setForm({ ...form, cover_letter: e.target.value })} className="min-h-[160px]" data-testid="court-cover-letter" />
          {others.length > 0 && (
            <div data-testid="court-extra-reports">
              <p className="text-sm font-medium">Also enclose other completed reports from your cases</p>
              <div className="mt-2 grid sm:grid-cols-2 gap-2">
                {others.map((o) => (
                  <label key={o.id} className="flex items-start gap-2 rounded-md border border-border px-3 py-2 text-sm cursor-pointer">
                    <input type="checkbox" checked={extra.includes(o.id)} onChange={(e) => setExtra(e.target.checked ? [...extra, o.id] : extra.filter((x) => x !== o.id))} className="mt-1" data-testid={`court-extra-${o.id}`} />
                    <span><span className="font-semibold tracking-wider">{o.case_code}</span> · {o.subject_label}{o.child_name ? ` · ${o.child_name}` : ""}{o.is_safety && <span className="ml-1 text-red-700 text-xs font-semibold">SAFETY</span>}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" checked={incOutcome} onChange={(e) => setIncOutcome(e.target.checked)} data-testid="court-include-outcome" /> Include recorded session outcome</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={incClosing} onChange={(e) => setIncClosing(e.target.checked)} data-testid="court-include-closing" /> Include closing summaries for closed cases</label>
          </div>
          <label className="flex items-start gap-2 rounded-md border border-align-yellow/60 bg-align-yellow/10 px-3 py-3 text-sm cursor-pointer" data-testid="court-attest-label">
            <input type="checkbox" checked={attest} onChange={(e) => setAttest(e.target.checked)} className="mt-1" data-testid="court-attest" />
            <span>{opts?.attestation_text}</span>
          </label>
          <div className="flex gap-2">
            <Button onClick={send} disabled={busy || !attest || !form.judge_name || !form.judge_email || form.cover_letter.trim().length < 40} data-testid="court-send-btn">{busy ? "Sending…" : "Send to court"}</Button>
            <Button variant="ghost" onClick={() => setOpen(false)} data-testid="court-cancel-btn">Cancel</Button>
          </div>
        </div>
      )}

      {packets.length > 0 && (
        <ul className="mt-5 divide-y divide-border" data-testid="court-packet-list">
          {packets.map((p) => {
            const [label, cls] = STATUS[p.status] || STATUS.sent;
            return (
              <li key={p.id} className="py-3" data-testid={`court-packet-${p.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm"><span className="font-semibold">{p.judge_name}</span> · {p.court_name || "court"}{p.cause_number ? ` · No. ${p.cause_number}` : ""}<div className="text-xs text-muted-foreground">Sent {p.created_at?.slice(0, 10)} · expires {p.expires_at?.slice(0, 10)} · {p.opened_count || 0} opens · {p.download_count || 0} downloads · {p.report_ids?.length || 1} report{p.report_ids?.length === 1 ? "" : "s"}</div></div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`} data-testid={`court-packet-status-${p.id}`}>{label}</span>
                    <Button size="sm" variant="outline" asChild data-testid={`court-packet-pdf-${p.id}`}><a href={`${process.env.REACT_APP_BACKEND_URL}/api/court-packets/${p.id}/pdf`} download><Download className="h-3.5 w-3.5" /></a></Button>
                    {p.status !== "revoked" && <>
                      <Button size="sm" variant="outline" onClick={() => act(p.id, "resend")} data-testid={`court-packet-resend-${p.id}`}><RefreshCw className="h-3.5 w-3.5" /></Button>
                      <Button size="sm" variant="outline" className="text-destructive" onClick={() => window.confirm("Revoke the court's access to this packet?") && act(p.id, "revoke")} data-testid={`court-packet-revoke-${p.id}`}><Ban className="h-3.5 w-3.5" /></Button>
                    </>}
                  </div>
                </div>
                {(p.responses || []).length > 0 && (
                  <ul className="mt-2 space-y-1 text-sm" data-testid={`court-packet-responses-${p.id}`}>
                    {p.responses.map((x) => <li key={x.id} className="rounded-md bg-secondary/50 px-3 py-2"><span className="font-semibold">{x.kind === "acknowledged" ? "Receipt acknowledged" : "Clarification requested"}</span> by {x.by} · {x.at?.slice(0, 16).replace("T", " ")}{x.message && <div className="mt-1 text-muted-foreground">{x.message}</div>}</li>)}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
