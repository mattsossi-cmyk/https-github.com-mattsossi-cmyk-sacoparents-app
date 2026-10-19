import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ExternalLink, Phone, ShieldCheck } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SafeContactStep } from "@/components/SafeContactStep";
import { QuickExitBar, quickExit } from "@/components/QuickExit";
import { useNavigate } from "react-router-dom";
import { CrisisResourcesButton } from "@/components/CrisisResources";
import { PROFESSIONAL_ACCESS_NOTICE, SAFETY_HUB_DECLINE } from "@/content/safetyEntry";

const Hotline = ({ resources, externalNote }) => (
  <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm" data-testid="screening-hotline">
    {resources.map((r) => (
      <p key={r.name} className="flex items-start gap-2" data-testid={`screening-resource-${r.external ? "external" : "phone"}`}>
        {r.external ? <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-red-700" /> : <Phone className="mt-0.5 h-4 w-4 shrink-0 text-red-700" />}
        <span>
          {r.external
            ? <><a href={r.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-brand-purple underline underline-offset-2" data-testid="screening-external-link">{r.name}</a> <span className="text-[11px] text-muted-foreground" data-testid="screening-external-note">({externalNote || "Opens in a new tab and leaves SA CoParents."})</span></>
            : <><strong>{r.name}</strong>{r.contact && <> — {r.contact}</>}{!r.verified && <span className="ml-1 text-[11px] text-muted-foreground">(verification pending)</span>}</>}
        </span>
      </p>
    ))}
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
  const [safeContact, setSafeContact] = useState(null);
  const [busy, setBusy] = useState(false);
  const [help, setHelp] = useState(false);
  const navigate = useNavigate();
  const onAnswer = (it, v) => {
    if (it.kind === "gate") {
      if (v === "Quick exit") { quickExit(); return; }
      if (v.startsWith("Not now")) { navigate("/dashboard", { replace: true }); return; }
    }
    setAnswers((a) => ({ ...a, [it.id]: v }));
  };
  useEffect(() => { api.get(`/joint/reports/${id}/safety-screening`).then((r) => { setData(r.data); if (r.data.my_draft) setAnswers(r.data.my_draft); }).catch((e) => toast.error(formatApiError(e))); }, [id]);
  useEffect(() => {
    if (!data?.spec || result || !Object.keys(answers).length) return undefined;
    const t = setTimeout(() => { api.put(`/joint/reports/${id}/safety-screening/draft`, { responses: answers }).catch(() => {}); }, 800);
    return () => clearTimeout(t);
  }, [answers, data, id, result]);
  if (!data) return <div className="min-h-screen bg-background" data-testid="screening-loading"><QuickExitBar /></div>;
  const spec = data.spec;
  const choose = async (version) => {
    setBusy(true);
    try { await api.put(`/joint/reports/${id}/safety-screening/choose`, { version }); const r = await api.get(`/joint/reports/${id}/safety-screening`); setData(r.data); window.scrollTo(0, 0); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const submit = async () => {
    setBusy(true);
    try { const { data: res } = await api.put(`/joint/reports/${id}/safety-screening`, { responses: answers, safe_contact: safeContact }); setResult(res); window.scrollTo(0, 0); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const parts = spec ? [...new Set(spec.items.map((i) => i.part))] : [];
  return (
    <div className="min-h-screen bg-background" data-testid="screening-page">
      <QuickExitBar notice={spec?.safe_device_notice} />
      <header className="bg-white border-b border-border"><div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-3"><Link to={`/joint/${id}/safety`} className="flex items-center gap-1.5 text-sm text-muted-foreground" data-testid="screening-back"><ArrowLeft className="h-4 w-4" /> Back to safety hub</Link><div className="flex items-center gap-3"><CrisisResourcesButton version={spec?.version || data.roles?.[data.my_role]?.version} /><BrandLogo size="text-xl" /></div></div></header>
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        {data.choice && (
          <div className="rounded-lg border border-border bg-white p-5 space-y-3" data-testid="screening-choice">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Screening questions, not a diagnostic tool</p>
            <h1 className="text-2xl font-semibold" data-testid="screening-choice-title">{data.choice.question}</h1>
            <p className="text-sm" data-testid="screening-choice-intro">{data.choice.intro}</p>
            <p className="rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs" data-testid="screening-choice-trigger-warning">{data.choice.trigger_warning}</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {data.choice.options.map((o) => <button key={o.version} type="button" disabled={busy} onClick={() => (o.version === "help" ? setHelp(true) : choose(o.version))} className={`rounded-lg border p-4 text-left text-sm font-medium hover:bg-brand-purple/5 ${o.version === "help" && help ? "border-brand-purple bg-brand-purple/5" : "border-brand-purple/30 bg-white"}`} data-testid={`screening-choice-${o.version}`}>{o.label}</button>)}
            </div>
            {help && (
              <div className="rounded-lg border border-brand-purple/20 bg-brand-purple/5 p-4 space-y-3" data-testid="screening-choice-help">
                <p className="text-sm" data-testid="screening-choice-help-text">{data.choice.options.find((o) => o.version === "help")?.help}</p>
                <div className="flex flex-wrap gap-2">
                  {data.choice.options.filter((o) => o.version !== "help").map((o) => <button key={o.version} type="button" disabled={busy} onClick={() => choose(o.version)} className="rounded-full border border-brand-purple/40 bg-white px-4 py-2 text-xs font-semibold text-brand-purple hover:bg-white/60" data-testid={`screening-choice-help-${o.version}`}>{o.label}</button>)}
                </div>
              </div>
            )}
            {data.choice.note && <p className="text-xs text-muted-foreground" data-testid="screening-choice-note">{data.choice.note}</p>}
            <p className="text-[11px] text-muted-foreground">Only the version you pick is saved. Your co-parent never sees this choice or your answers.</p>
          </div>
        )}
        {!spec && !data.choice && <div className="rounded-lg border border-border bg-white p-5 text-sm" data-testid="screening-unassigned">Your professional has not assigned a screening version yet. Please check back shortly.</div>}
        {spec && result && (
          <div className="space-y-4" data-testid="screening-result">
            <div className={`rounded-lg border p-5 ${result.tier === 3 ? "border-amber-300 bg-amber-50" : "border-align-green/40 bg-align-green/10"}`}>
              <p className="flex items-center gap-2 text-sm font-bold"><ShieldCheck className="h-5 w-5" /> Thank you. Your answers were saved privately for your professional.</p>
              {result.tier_label && <p className="mt-2 text-sm" data-testid="screening-result-tier">{result.tier_label}</p>}
              {result.close_note && <p className="mt-2 text-sm" data-testid="screening-result-close">{result.close_note}</p>}
              <p className="mt-1 text-xs text-muted-foreground">{result.answered_count} answered · {result.skipped_count} skipped. {result.scale_note}</p>
            </div>
            {result.tier >= 2 && !result.close_note && <p className="text-sm" data-testid="screening-result-followup">{result.tier === 3 ? "Please consider reaching out to the hotline below and making a simple safety plan — where you could go, who you could call, what you would take. Your professional has been flagged to follow up with you." : "Your professional may suggest a follow-up conversation. The resources below are available any time."}</p>}
            <Hotline resources={result.resources} externalNote={result.external_link_note} />
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
              <p className="mt-2 rounded-md border border-[#3D1A78]/20 bg-[#3D1A78]/5 p-2 text-xs leading-relaxed" data-testid="screening-access-notice">{PROFESSIONAL_ACCESS_NOTICE} <Link to="/privacy-notice" className="font-semibold text-brand-purple underline underline-offset-2" data-testid="screening-privacy-notice-link">Read the privacy notification</Link></p>
              <Hotline resources={spec.resources} externalNote={spec.external_link_note} />
            </div>
            {parts.map((part) => (
              <section key={part} className="space-y-2" data-testid={`screening-part-${part.split(" ")[0].replace(/[^A-Za-z0-9]/g, "").toLowerCase()}`}>
                <h2 className="text-base md:text-lg font-semibold text-brand-purple">{part}</h2>
                {spec.items.filter((i) => i.part === part && (!i.follow || (answers[i.follow] && answers[i.follow] !== "Never" && answers[i.follow] !== "Prefer not to answer"))).map((it) => (
                  <div key={it.id}>
                    <Item it={it} scales={spec.scales} value={answers[it.id]} onChange={(v) => onAnswer(it, v)} />
                    {it.id === "danger" && answers.danger === "Yes" && spec.emergency && (
                      <div className="mt-2 rounded-lg border-2 border-red-400 bg-red-50 p-4" role="alert" data-testid="screening-emergency">
                        <p className="text-sm font-bold text-red-800">{spec.emergency.title}</p>
                        {spec.emergency.lines.map((l) => <p key={l} className="mt-1 text-sm text-red-900">{l}</p>)}
                        <p className="mt-2 text-xs text-red-800">{spec.emergency.note}</p>
                        <div className="mt-2 flex gap-2"><CrisisResourcesButton /><button type="button" onClick={quickExit} className="rounded-full bg-red-700 px-4 py-1.5 text-xs font-bold text-white" data-testid="screening-emergency-quick-exit">Quick exit</button></div>
                      </div>
                    )}
                  </div>
                ))}
              </section>
            ))}
            <SafeContactStep value={safeContact} onChange={setSafeContact} />
            <p className="text-[11px] text-muted-foreground" data-testid="screening-source">{spec.source} {spec.scale_note}</p>
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={submit} disabled={busy} data-testid="screening-submit-btn">Submit privately</Button>
              <button type="button" disabled={busy} onClick={async () => { try { await api.post(`/joint/reports/${id}/safety-screening/decline`); } catch { /* status only; never block the parent */ } navigate("/dashboard", { replace: true }); }} className="rounded-full border border-[#3D1A78]/40 px-5 py-2 text-sm font-semibold text-[#3D1A78] transition-colors hover:bg-[#3D1A78]/5 disabled:opacity-50" data-testid="screening-decline-btn">{SAFETY_HUB_DECLINE}</button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
