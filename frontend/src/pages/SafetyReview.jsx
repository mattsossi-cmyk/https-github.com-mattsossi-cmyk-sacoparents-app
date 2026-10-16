import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Lock, Download } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";

const TIER_CLS = { red: "bg-red-100 text-red-900 border-red-300", amber: "bg-amber-100 text-amber-900 border-amber-300", green: "bg-emerald-100 text-emerald-900 border-emerald-300" };

const Column = ({ c }) => (
  <div className="rounded-lg border border-border bg-white p-4" data-testid={`review-col-${c.role}`}>
    <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">{c.label}</p>
    <p className="mt-1 text-sm" data-testid={`review-col-${c.role}-entry`}>{c.entry_label || "Not started"}</p>
    {c.received && <span className={`mt-2 inline-block rounded-md border px-2 py-0.5 text-xs font-semibold ${TIER_CLS[c.app_tier] || ""}`} data-testid={`review-col-${c.role}-tier`}>{c.app_tier_label}</span>}
    {c.completed_at && <p className="mt-1 text-xs text-muted-foreground">Completed {c.completed_at.slice(0, 10)}</p>}
    <div className="mt-3" data-testid={`review-col-${c.role}-pattern`}>
      <p className="text-xs font-semibold">Pattern panel</p>
      {c.pattern.length === 0 && <p className="text-xs text-muted-foreground">{c.received ? "No signals triggered." : "Awaiting check-in."}</p>}
      <ul className="mt-1 space-y-1">{c.pattern.map((p) => <li key={p.domain} className="text-xs"><span className="font-medium">{p.domain}:</span> {p.signals.join("; ")}</li>)}</ul>
    </div>
    {c.pathway?.confirmed && <p className="mt-2 text-xs text-muted-foreground" data-testid={`review-col-${c.role}-pathway`}>Pathway confirmed: {c.pathway.confirmed.replace("_", " ")}</p>}
  </div>
);

export default function SafetyReview() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  const [rev, setRev] = useState(null);
  const [custom, setCustom] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get(`/joint/reports/${id}/safety-review`).then((r) => { setD(r.data); setRev(r.data.review); }).catch((e) => toast.error(formatApiError(e))); }, [id]);
  const toggle = (key, v) => setRev((x) => ({ ...x, [key]: x[key].includes(v) ? x[key].filter((i) => i !== v) : [...x[key], v] }));
  const save = async () => {
    setBusy(true);
    try { const r = await api.put(`/joint/reports/${id}/safety-review`, { ...rev, custom_provisions: custom.split("\n").map((s) => s.trim()).filter(Boolean) }); setRev({ ...r.data, custom_provisions: r.data.custom_provisions }); toast.success("Safety review saved"); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const exportPdf = async () => {
    try {
      const r = await api.get(`/joint/reports/${id}/safety-review/provisions.pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data); const a = document.createElement("a"); a.href = url; a.download = "provisions.pdf"; a.click(); URL.revokeObjectURL(url);
      toast.success("Export scan passed — provisions downloaded");
    } catch (e) { toast.error(e?.response?.status === 409 ? "Export blocked: the document contains screening wording." : formatApiError(e)); }
  };
  useEffect(() => { if (d?.review?.custom_provisions) setCustom(d.review.custom_provisions.join("\n")); }, [d]);
  if (!d || !rev) return <div className="min-h-screen bg-background" data-testid="safety-review-loading" />;
  const groups = [...new Set(d.provisions.map((p) => p.group))];
  return (
    <div className="min-h-screen bg-background" data-testid="safety-review-page">
      <header className="bg-white border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between"><Link to={`/joint/${id}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground" data-testid="safety-review-back"><ArrowLeft className="h-4 w-4" /> Back to case</Link><BrandLogo size="text-xl" /></div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand-purple"><Lock className="h-3.5 w-3.5" /> Professional-only · access logged</p>
          <h1 className="mt-1 text-2xl font-semibold" data-testid="safety-review-title">Safety review</h1>
          <p className="mt-2 rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs" data-testid="safety-review-notice">{d.notice}</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2" data-testid="safety-review-columns">{d.columns.map((c) => <Column key={c.role} c={c} />)}</div>
        <section className="rounded-lg border border-border bg-white p-5 space-y-4" data-testid="safety-review-decision">
          <h2 className="text-base font-semibold md:text-lg">Concern level (your decision)</h2>
          <div className="flex flex-wrap gap-2">{d.levels.map((l) => <button key={l.id} type="button" onClick={() => setRev((x) => ({ ...x, concern_level: l.id }))} className={`rounded-full border px-3 py-1.5 text-sm ${rev.concern_level === l.id ? "border-brand-purple bg-brand-purple text-white" : "border-border bg-white hover:bg-muted"}`} data-testid={`concern-level-${l.id}`}>{l.label}</button>)}</div>
          <div>
            <p className="text-sm font-semibold">Reasons</p>
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">{d.reasons.map((r) => <li key={r} className="flex items-start gap-2 text-sm"><Checkbox checked={rev.reasons.includes(r)} onCheckedChange={() => toggle("reasons", r)} data-testid={`reason-${d.reasons.indexOf(r)}`} /><span>{r}</span></li>)}</ul>
          </div>
          <div>
            <p className="text-sm font-semibold">Notes (professional-only)</p>
            <Textarea value={rev.notes} onChange={(e) => setRev((x) => ({ ...x, notes: e.target.value }))} className="mt-1" rows={3} data-testid="safety-review-notes" />
          </div>
        </section>
        <section className="rounded-lg border border-border bg-white p-5 space-y-4" data-testid="provisions-library">
          <h2 className="text-base font-semibold md:text-lg">Provisions library</h2>
          {groups.map((g) => (
            <div key={g}>
              <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">{g}</p>
              <ul className="mt-2 space-y-2">{d.provisions.filter((p) => p.group === g).map((p) => <li key={p.id} className="flex items-start gap-2 text-sm"><Checkbox checked={rev.provisions.includes(p.id)} onCheckedChange={() => toggle("provisions", p.id)} data-testid={`provision-${p.id}`} /><span>{p.text}</span></li>)}</ul>
            </div>
          ))}
          <div>
            <p className="text-sm font-semibold">Additional provisions (one per line)</p>
            <Textarea value={custom} onChange={(e) => setCustom(e.target.value)} className="mt-1" rows={3} data-testid="custom-provisions" />
          </div>
          <p className="text-xs text-muted-foreground" data-testid="provisions-footer">{d.footer}</p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={save} disabled={busy} data-testid="safety-review-save">Save review</Button>
            <Button variant="outline" onClick={exportPdf} data-testid="provisions-export"><Download className="mr-1 h-4 w-4" /> Export provisions (scanned)</Button>
          </div>
        </section>
      </main>
    </div>
  );
}
