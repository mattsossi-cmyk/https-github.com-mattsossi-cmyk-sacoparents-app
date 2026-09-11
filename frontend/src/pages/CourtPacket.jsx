import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { Download, Gavel, ShieldCheck, CheckCircle2, MessageSquare } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { BrandLogo } from "@/components/Brand";
import { CourtReportView } from "@/components/CourtReportView";

const KEY = (t) => `court-access-${t}`;

export default function CourtPacket() {
  const { token } = useParams();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [code, setCode] = useState("");
  const [access, setAccess] = useState(() => sessionStorage.getItem(KEY(token)) || "");
  const [packet, setPacket] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.get(`/court/${token}/preview`).then((r) => setPreview(r.data)).catch((e) => setError(formatApiError(e)));
  }, [token]);

  useEffect(() => {
    if (!access) return;
    api.get(`/court/${token}`, { headers: { "X-Court-Access": access } })
      .then((r) => setPacket(r.data))
      .catch(() => { sessionStorage.removeItem(KEY(token)); setAccess(""); });
  }, [token, access]);

  const unlock = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/court/${token}/unlock`, { code: code.trim() });
      sessionStorage.setItem(KEY(token), data.access);
      setAccess(data.access);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const respond = async (kind) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/court/${token}/respond`, { kind, message: msg }, { headers: { "X-Court-Access": access } });
      setPacket((p) => ({ ...p, responses: [...(p.responses || []), data.response], status: kind === "acknowledged" ? "acknowledged" : "clarification_requested" }));
      setMsg("");
      toast.success(kind === "acknowledged" ? "Receipt acknowledged — the professional has been notified" : "Clarification request sent to the professional");
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  if (error) return <Shell><p className="text-destructive" data-testid="court-error">{error}</p></Shell>;
  if (!preview) return <Shell><p className="text-muted-foreground" data-testid="court-loading">Loading…</p></Shell>;
  if (preview.state !== "active") {
    return <Shell><div data-testid="court-unavailable"><h1 className="text-2xl font-semibold">This Court Packet is {preview.state}</h1><p className="mt-2 text-muted-foreground">Please contact {preview.professional_name} to request a new packet.</p></div></Shell>;
  }

  if (!packet) {
    return (
      <Shell>
        <div className="max-w-md" data-testid="court-unlock">
          <p className="text-xs uppercase tracking-widest text-accent font-semibold">Court Packet</p>
          <h1 className="text-2xl font-semibold mt-1">{preview.court_name || "For the Court"}</h1>
          <p className="mt-1 text-sm text-muted-foreground">Prepared by {preview.professional_name}{preview.cause_number ? ` · Cause No. ${preview.cause_number}` : ""} · Addressed to {preview.judge_name}</p>
          <p className="mt-6 text-sm">Enter the 6-digit access code that was emailed to you separately.</p>
          <div className="mt-3 flex gap-2">
            <Input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" placeholder="000000" className="h-11 text-lg tracking-[0.4em] font-semibold" data-testid="court-code-input" />
            <Button onClick={unlock} disabled={busy || code.length !== 6} className="h-11" data-testid="court-unlock-btn">{busy ? "Checking…" : "Open packet"}</Button>
          </div>
          <p className="mt-6 text-xs text-muted-foreground flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> Read-only. Every opening and download is logged for the professional. Access expires {preview.expires_at?.slice(0, 10)}.</p>
        </div>
      </Shell>
    );
  }

  const pro = packet.professional || {};
  return (
    <Shell wide>
      <div className="flex flex-wrap items-start justify-between gap-4" data-testid="court-packet">
        <div>
          <p className="text-xs uppercase tracking-widest text-accent font-semibold flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Court Packet · read-only</p>
          <h1 className="text-2xl sm:text-3xl font-semibold mt-1" data-testid="court-packet-title">{packet.court_name || "For the Court"}{packet.cause_number ? ` — Cause No. ${packet.cause_number}` : ""}</h1>
          <p className="mt-1 text-sm text-muted-foreground">Addressed to {packet.judge_name} · Sent {packet.created_at?.slice(0, 10)} · Expires {packet.expires_at?.slice(0, 10)}</p>
        </div>
        <Button asChild className="gap-2" data-testid="court-download-btn">
          <a href={`${process.env.REACT_APP_BACKEND_URL}/api/court/${token}/pdf?access=${encodeURIComponent(access)}`} download><Download className="h-4 w-4" /> Download combined PDF</a>
        </Button>
      </div>

      <section className="report-paper rounded-lg p-8 sm:p-12 mt-8" data-testid="court-cover-letter">
        <div className="border-b border-border pb-5 mb-6">
          <p className="text-xl font-semibold text-brand-purple">{pro.name}</p>
          <p className="text-sm text-muted-foreground">{[pro.pro_role, pro.organization].filter(Boolean).join(" · ")}</p>
          <p className="text-sm text-muted-foreground">{[pro.license_number && `License ${pro.license_number}`, pro.phone, pro.email].filter(Boolean).join(" · ")}</p>
          {pro.credentials_verified && <p className="mt-1 text-xs font-semibold text-accent flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" /> Credentials verified by SA CoParents</p>}
        </div>
        <p className="text-sm">{packet.created_at?.slice(0, 10)}</p>
        <p className="mt-3 text-sm">The Honorable {packet.judge_name}<br />{packet.court_name}{packet.cause_number ? <><br />Re: Cause No. {packet.cause_number}</> : null}</p>
        <div className="mt-6 whitespace-pre-wrap text-[15px] leading-relaxed" data-testid="court-letter-body">{packet.cover_letter}</div>
        {packet.session_outcome && (packet.session_outcome.chosen_steps?.length > 0 || packet.session_outcome.summary) && (
          <div className="mt-8 rounded-lg bg-secondary/50 p-4" data-testid="court-session-outcome">
            <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Session outcome recorded by the professional</p>
            <ul className="mt-2 space-y-1 text-sm">{(packet.session_outcome.chosen_steps || []).map((s) => <li key={s} className="flex gap-2"><CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" />{s}</li>)}</ul>
            {packet.session_outcome.summary && <p className="mt-2 text-sm italic">{packet.session_outcome.summary}</p>}
          </div>
        )}
        <div className="mt-8 border-t border-border pt-4 text-xs text-muted-foreground" data-testid="court-attestation">
          <p className="font-semibold uppercase tracking-widest">Professional attestation · {packet.attested_at?.slice(0, 10)}</p>
          <p className="mt-1 italic">{packet.attestation_text}</p>
        </div>
      </section>

      {(packet.reports || []).map((r, i) => <CourtReportView key={r.id} item={r} index={i + 1} />)}

      <section className="bg-white border border-border rounded-lg p-6 mt-8" data-testid="court-respond">
        <h2 className="text-lg font-semibold flex items-center gap-2"><MessageSquare className="h-4 w-4" /> Respond to the professional</h2>
        <p className="text-sm text-muted-foreground mt-1">Your response is sent privately to {pro.name}. Parents do not see it.</p>
        {(packet.responses || []).length > 0 && (
          <ul className="mt-3 space-y-2 text-sm" data-testid="court-responses">
            {packet.responses.map((x) => <li key={x.id} className="rounded-md bg-secondary/50 px-3 py-2"><span className="font-semibold">{x.kind === "acknowledged" ? "Receipt acknowledged" : "Clarification requested"}</span> · {x.at?.slice(0, 16).replace("T", " ")}{x.message && <div className="mt-1 text-muted-foreground">{x.message}</div>}</li>)}
          </ul>
        )}
        <Textarea value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Optional note, or describe what needs clarification…" className="mt-4 min-h-[80px]" data-testid="court-respond-message" />
        <div className="mt-3 flex flex-wrap gap-2">
          <Button onClick={() => respond("acknowledged")} disabled={busy} data-testid="court-acknowledge-btn">Acknowledge receipt</Button>
          <Button variant="outline" onClick={() => respond("clarification")} disabled={busy || !msg.trim()} data-testid="court-clarify-btn">Request clarification</Button>
        </div>
      </section>
    </Shell>
  );
}

function Shell({ children, wide }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-white"><div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between"><BrandLogo size="text-xl" /><span className="text-xs text-muted-foreground">Court access</span></div></header>
      <main className={`${wide ? "max-w-5xl" : "max-w-3xl"} mx-auto px-6 py-10`}>{children}</main>
    </div>
  );
}
