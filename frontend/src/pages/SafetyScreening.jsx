import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Phone, ShieldCheck } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const Hotline = ({ resources }) => (
  <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm" data-testid="screening-hotline">
    {resources.map((r) => <p key={r.name} className="flex items-start gap-2"><Phone className="mt-0.5 h-4 w-4 shrink-0 text-red-700" /><span><strong>{r.name}</strong> — {r.contact}{!r.verified && <span className="ml-1 text-[11px] text-muted-foreground">(verification pending)</span>}</span></p>)}
  </div>
);

const Item = ({ it, scales, value, onChange }) => {
  const opts = scales[it.kind];
  return (
    <div className="rounded-md border border-border bg-white p-3" data-testid={`screening-item-${it.id}`}>
      {it.stem && <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{it.stem}</p>}
      <p className="text-sm font-medium">{it.text}</p>
      {it.kind === "text" ? <Textarea value={value || ""} onChange={(e) => onChange(e.target.value)} className="mt-2 bg-white" placeholder="Optional — leave blank to skip" data-testid={`screening-answer-${it.id}`} /> : (
        <div className="mt-2 flex flex-wrap gap-2">
          {opts.map((o) => <button key={o} type="button" onClick={() => onChange(value === o ? "" : o)} className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${value === o ? "border-brand-purple bg-brand-purple text-white" : "border-border bg-white hover:bg-secondary"}`} data-testid={`screening-answer-${it.id}-${o.toLowerCase().replace(/[^a-z]+/g, "-")}`}>{o}</button>)}
          <button type="button" onClick={() => onChange("")} className="rounded-full px-3 py-1 text-xs text-muted-foreground hover:underline" data-testid={`screening-skip-${it.id}`}>Skip</button>
        </div>
      )}
    </div>
  );
};

export default function SafetyScreening() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get(`/joint/reports/${id}/safety-screening`).then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e))); }, [id]);
  if (!data) return <div className="min-h-screen bg-background" data-testid="screening-loading" />;
  const spec = data.spec;
  const submit = async () => {
    setBusy(true);
    try { const { data: res } = await api.put(`/joint/reports/${id}/safety-screening`, { responses: answers }); setResult(res); window.scrollTo(0, 0); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const parts = spec ? [...new Set(spec.items.map((i) => i.part))] : [];
  return (
    <div className="min-h-screen bg-background" data-testid="screening-page">
      <header className="bg-white border-b border-border"><div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between"><Link to={`/joint/${id}`} className="flex items-center gap-1.5 text-sm text-muted-foreground" data-testid="screening-back"><ArrowLeft className="h-4 w-4" /> Back to case</Link><BrandLogo size="text-xl" /></div></header>
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        {!spec && <div className="rounded-lg border border-border bg-white p-5 text-sm" data-testid="screening-unassigned">Your professional has not assigned a screening version yet. Please check back shortly.</div>}
        {spec && result && (
          <div className="space-y-4" data-testid="screening-result">
            <div className={`rounded-lg border p-5 ${result.tier === 3 ? "border-amber-300 bg-amber-50" : "border-align-green/40 bg-align-green/10"}`}>
              <p className="flex items-center gap-2 text-sm font-bold"><ShieldCheck className="h-5 w-5" /> Thank you. Your answers were saved privately for your professional.</p>
              <p className="mt-2 text-sm" data-testid="screening-result-tier">{result.tier_label}</p>
              <p className="mt-1 text-xs text-muted-foreground">{result.answered_count} answered · {result.skipped_count} skipped. {result.scale_note}</p>
            </div>
            {result.tier >= 2 && <p className="text-sm" data-testid="screening-result-followup">{result.tier === 3 ? "Please consider reaching out to the hotline below and making a simple safety plan — where you could go, who you could call, what you would take. Your professional has been flagged to follow up with you." : "Your professional may suggest a follow-up conversation. The resources below are available any time."}</p>}
            <Hotline resources={result.resources} />
            <Link to={`/joint/${id}`}><Button data-testid="screening-done-btn">Return to case</Button></Link>
          </div>
        )}
        {spec && !result && (
          <>
            <div className="rounded-lg border border-border bg-white p-5" data-testid="screening-intro">
              <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">{spec.label}</p>
              <h1 className="mt-1 text-2xl font-semibold" data-testid="screening-title">{spec.title}</h1>
              <p className="mt-3 text-sm" data-testid="screening-intro-text">{spec.intro}</p>
              <p className="mt-2 rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs" data-testid="screening-trigger-warning">{spec.trigger_warning}</p>
              <Hotline resources={spec.resources} />
            </div>
            {parts.map((part) => (
              <section key={part} className="space-y-2" data-testid={`screening-part-${part.split(" ")[0].replace(/[^A-Za-z0-9]/g, "").toLowerCase()}`}>
                <h2 className="text-base md:text-lg font-semibold text-brand-purple">{part}</h2>
                {spec.items.filter((i) => i.part === part).map((it) => <Item key={it.id} it={it} scales={spec.scales} value={answers[it.id]} onChange={(v) => setAnswers((a) => ({ ...a, [it.id]: v }))} />)}
              </section>
            ))}
            <p className="text-[11px] text-muted-foreground" data-testid="screening-source">{spec.source} {spec.scale_note}</p>
            <Button onClick={submit} disabled={busy} data-testid="screening-submit-btn">Submit privately</Button>
          </>
        )}
      </main>
    </div>
  );
}
