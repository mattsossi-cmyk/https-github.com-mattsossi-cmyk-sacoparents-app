import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Lock } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { PathwayDecision } from "@/components/PathwayDecision";

export default function SafetyResponses() {
  const { id, role } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { api.get(`/joint/reports/${id}/safety-screening/${role}/responses`).then((r) => setD(r.data)).catch((e) => { setErr(formatApiError(e)); toast.error(formatApiError(e)); }); }, [id, role]);
  return (
    <div className="min-h-screen bg-background" data-testid="screening-responses-page">
      <header className="bg-white border-b border-border"><div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between"><Link to={`/joint/${id}`} className="flex items-center gap-1.5 text-sm text-muted-foreground" data-testid="screening-responses-back"><ArrowLeft className="h-4 w-4" /> Back to case</Link><BrandLogo size="text-xl" /></div></header>
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        {err && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800" data-testid="screening-responses-error">{err}</p>}
        {d && (
          <>
            <div className="rounded-lg border border-border bg-white p-5">
              <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand-purple"><Lock className="h-3.5 w-3.5" /> Professional-only · access logged</p>
              <h1 className="mt-1 text-2xl font-semibold" data-testid="screening-responses-title">{d.status.name} — {d.status.version_label}</h1>
              <p className="mt-1 text-sm" data-testid="screening-responses-tier">{d.status.tier_label || "Tier not available"} · completed {(d.status.completed_at || "").slice(0, 10)} · {d.status.source}</p>
              <p className="mt-2 rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs" data-testid="screening-responses-notice">{d.notice}</p>
            </div>
            {d.pathway && <PathwayDecision rid={id} role={role} pathway={d.pathway} onChange={(dec) => setD((x) => ({ ...x, pathway: { ...x.pathway, decision: dec } }))} />}
            <ul className="space-y-2" data-testid="screening-responses-list">
              {d.items.map((it, i) => <li key={it.id || i} className={`rounded-md border p-3 text-sm ${it.flag ? "border-amber-300 bg-amber-50" : "border-border bg-white"}`} data-testid={`screening-response-${it.id || i}`}>{it.part && <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{it.part}</p>}<p className="font-medium">{it.question}</p><p className="mt-1 text-brand-purple" data-testid={`screening-response-${it.id || i}-answer`}>{it.answer}</p></li>)}
            </ul>
            <p className="text-[11px] text-muted-foreground">{d.source_credit} {d.scale_note}</p>
          </>
        )}
      </main>
    </div>
  );
}
