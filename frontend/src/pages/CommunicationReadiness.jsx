import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, MessageSquareText } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { QuickExitBar } from "@/components/QuickExit";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function CommunicationReadiness() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  const [a, setA] = useState({});
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get(`/joint/reports/${id}/communication-readiness`).then((r) => setD(r.data)).catch((e) => toast.error(formatApiError(e))); }, [id]);
  const submit = async () => {
    setBusy(true);
    try { const { data } = await api.put(`/joint/reports/${id}/communication-readiness`, { responses: a }); setDone(data); window.scrollTo(0, 0); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900" data-testid="comm-page">
      <QuickExitBar variant="red" label="Confidential Assessment Area" />
      <header className="border-b border-[#3D1A78]/10 bg-white"><div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-6"><Link to={`/joint/${id}/safety`} className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-[#3D1A78]" data-testid="comm-back"><ArrowLeft className="h-4 w-4" /> Back to safety hub</Link><span className="text-sm font-bold text-[#3D1A78]">SA CoParents</span></div></header>
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-8 sm:px-6">
        {done ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5" data-testid="comm-result">
            <p className="text-sm font-bold text-emerald-900">Thank you. Your answers were saved privately for your professional.</p>
            <p className="mt-1 text-xs text-emerald-900/80">{done.answered_count} answered. {done.note}</p>
            <Link to={`/joint/${id}/safety`} className="mt-4 inline-block"><Button className="bg-[#3D1A78] hover:bg-[#2f1460]" data-testid="comm-done-btn">Return to safety hub</Button></Link>
          </div>
        ) : d && (
          <>
            <div className="rounded-2xl border border-[#3D1A78]/15 bg-white p-5">
              <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[#3D1A78]"><MessageSquareText className="h-4 w-4" /> Communication Readiness</p>
              <h1 className="mt-1 text-2xl font-bold" data-testid="comm-title">Which communication approach feels safest for your family?</h1>
              <p className="mt-2 text-sm text-slate-700" data-testid="comm-note">{d.note}</p>
              {d.received && <p className="mt-2 text-xs font-semibold text-emerald-700" data-testid="comm-already">You already completed this on {(d.completed_at || "").slice(0, 10)}. Submitting again replaces your earlier answers.</p>}
            </div>
            {d.items.map((it) => (
              <fieldset key={it.id} className="rounded-2xl border border-[#3D1A78]/15 bg-white p-4" data-testid={`comm-item-${it.id}`}>
                <legend className="px-1 text-sm font-semibold">{it.text}</legend>
                {it.kind === "text" ? <Textarea value={a[it.id] || ""} onChange={(e) => setA({ ...a, [it.id]: e.target.value })} className="mt-2 bg-white" placeholder="Optional — leave blank to skip" data-testid={`comm-answer-${it.id}`} /> : (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {it.options.map((o) => <button key={o} type="button" aria-pressed={a[it.id] === o} onClick={() => setA({ ...a, [it.id]: a[it.id] === o ? "" : o })} className={`rounded-full border px-3 py-1.5 text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#3D1A78] ${a[it.id] === o ? "border-[#3D1A78] bg-[#3D1A78] text-white" : "border-slate-300 bg-white hover:bg-[#3D1A78]/5"}`} data-testid={`comm-answer-${it.id}-${o.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>{o}</button>)}
                    <button type="button" onClick={() => setA({ ...a, [it.id]: "" })} className="px-3 py-1.5 text-xs text-slate-500 hover:underline" data-testid={`comm-skip-${it.id}`}>Skip</button>
                  </div>
                )}
              </fieldset>
            ))}
            <Button onClick={submit} disabled={busy} className="bg-[#3D1A78] hover:bg-[#2f1460]" data-testid="comm-submit-btn">Save privately</Button>
          </>
        )}
      </main>
    </div>
  );
}
