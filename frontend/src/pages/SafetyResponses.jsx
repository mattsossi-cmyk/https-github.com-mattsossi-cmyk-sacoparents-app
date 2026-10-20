import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { trainingRedirect } from "@/lib/trainingGate";
import { toast } from "sonner";
import { ArrowLeft, Lock } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { PathwayDecision } from "@/components/PathwayDecision";
import { BridgeSafeContact } from "@/components/BridgeSafeContact";
import { CrisisResourcesButton } from "@/components/CrisisResources";

export default function SafetyResponses() {
  const { id, role } = useParams();
  const navigate = useNavigate();
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { api.get(`/joint/reports/${id}/safety-screening/${role}/responses`).then((r) => setD(r.data)).catch((e) => { if (trainingRedirect(e, navigate)) return; setErr(formatApiError(e)); toast.error(formatApiError(e)); }); }, [id, role]);
  return (
    <div className="min-h-screen bg-background" data-testid="screening-responses-page">
      <header className="bg-white border-b border-border"><div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between"><Link to={`/joint/${id}`} className="flex items-center gap-1.5 text-sm text-muted-foreground" data-testid="screening-responses-back"><ArrowLeft className="h-4 w-4" /> Back to case</Link><div className="flex items-center gap-3"><CrisisResourcesButton version={d?.status?.version} /><BrandLogo size="text-xl" /></div></div></header>
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        {err && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800" data-testid="screening-responses-error">{err}</p>}
        {d && (
          <>
            <div className="rounded-lg border border-border bg-white p-5">
              <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand-purple"><Lock className="h-3.5 w-3.5" /> Professional-only · access logged</p>
              <h1 className="mt-1 text-2xl font-semibold" data-testid="screening-responses-title">{d.status.name}{d.status.version_label ? ` — ${d.status.version_label}` : ""}</h1>
              <p className="mt-1 text-sm" data-testid="screening-responses-tier">{d.status.tier_label || "Tier not available"} · completed {(d.status.completed_at || "").slice(0, 10)} · {d.status.source}</p>
              <p className="mt-2 rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs" data-testid="screening-responses-notice">{d.notice}</p>
            </div>
            {d.pathway && <PathwayDecision rid={id} role={role} pathway={d.pathway} onChange={(dec) => setD((x) => ({ ...x, pathway: { ...x.pathway, decision: dec } }))} />}
            {d.communication?.received ? (
              <div className={`rounded-lg border p-4 ${d.communication.flag_for_professional ? "border-amber-300 bg-amber-50" : "border-border bg-white"}`} data-testid="comm-responses">
                <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Communication readiness — private flag input</p>
                <p className="mt-1 text-xs text-muted-foreground">{d.communication.note} Completed {(d.communication.completed_at || "").slice(0, 10)} · {d.communication.source}{d.communication.flag_for_professional ? " · flagged for your attention" : ""}</p>
                <ul className="mt-2 space-y-1.5 text-sm">{d.communication.items.map((it) => <li key={it.id} data-testid={`comm-response-${it.id}`}><span className="font-medium">{it.question}</span> <span className="text-brand-purple" data-testid={`comm-response-${it.id}-answer`}>{it.answer}</span></li>)}</ul>
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-border bg-white p-3 text-sm text-muted-foreground" data-testid="comm-not-completed">Communication readiness: not completed by this parent.</p>
            )}
            {d.not_completed && <p className="rounded-lg border border-dashed border-border bg-white p-4 text-sm text-muted-foreground" data-testid="screening-not-completed">Family check-in: not completed by this parent. There are no answers to review.</p>}
            <ul className="space-y-2" data-testid="screening-responses-list">
              {d.items.map((it, i) => <li key={it.id || i} className={`rounded-md border p-3 text-sm ${it.flag ? "border-amber-300 bg-amber-50" : "border-border bg-white"}`} data-testid={`screening-response-${it.id || i}`}>{it.part && <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{it.part}</p>}<p className="font-medium">{it.question}</p><p className="mt-1 text-brand-purple" data-testid={`screening-response-${it.id || i}-answer`}>{it.answer}</p></li>)}
            </ul>
            <BridgeSafeContact rid={id} role={role} />
            {d.safe_contact && (
              <div className="rounded-md border border-brand-purple/30 bg-brand-purple/5 p-3 text-sm" data-testid="screening-safe-contact-view">
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Safe way to reach this parent · professional-only, never in reports</p>
                <p><strong>Method:</strong> {d.safe_contact.method || "—"} {d.safe_contact.address && <>· {d.safe_contact.address}</>}</p>
                {d.safe_contact.safe_times && <p><strong>Safe times:</strong> {d.safe_contact.safe_times}</p>}
                {d.safe_contact.voicemail_ok && <p><strong>Voicemail/message OK:</strong> {d.safe_contact.voicemail_ok}</p>}
                {d.safe_contact.code_word && <p><strong>Code word:</strong> {d.safe_contact.code_word}</p>}
              </div>
            )}
            <p className="text-[11px] text-muted-foreground">{d.source_credit} {d.scale_note}</p>
          </>
        )}
      </main>
    </div>
  );
}
