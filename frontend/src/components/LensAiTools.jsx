import { useEffect, useState } from "react";
import { BookOpen, Globe, ScanSearch, ShieldCheck, Sparkles, Tags } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const ISSUE = { custody_recommendation: "Custody recommendation", diagnosis: "Diagnosis", credibility_judgment: "Credibility judgment", legal_conclusion: "Legal conclusion", characterization: "Characterization" };

export function NeutralityCheck({ id, rep }) {
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try { const { data } = await api.post(`/cases/${id}/professional-report/neutrality-check`, { fields: rep }); setRes(data); toast[data.flags.length ? "warning" : "success"](data.flags.length ? `${data.flags.length} sentence(s) flagged for review` : "No court-neutrality issues detected"); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div data-testid="lens-neutrality">
      <Button variant="outline" size="sm" onClick={run} disabled={busy} data-testid="lens-neutrality-btn"><ShieldCheck className="h-4 w-4 mr-1" /> {busy ? "Checking…" : "Court-neutrality check"}</Button>
      {res && (
        <div className={`mt-2 rounded-md border-l-4 p-3 text-xs ${res.flags.length ? "border-amber-500 bg-amber-50" : "border-align-green bg-[#eaf7f1]"}`} data-testid="lens-neutrality-result">
          <p className="font-semibold">{res.flags.length ? `${res.flags.length} sentence(s) may read as a custody recommendation, diagnosis, credibility judgment or legal conclusion:` : "No issues detected in the narrative sections."} <span className="font-normal text-muted-foreground">{res.note}</span></p>
          <ul className="mt-1 space-y-1">{res.flags.map((f, i) => <li key={i} data-testid={`lens-neutrality-flag-${i}`}><span className="rounded bg-amber-200 px-1 font-semibold">{ISSUE[f.issue] || f.issue}</span> <span className="text-muted-foreground">({f.field.replace(/_/g, " ")})</span> — “{f.sentence}”</li>)}</ul>
        </div>
      )}
    </div>
  );
}

export function ChildFocusSuggest({ id, value = {}, onChange }) {
  const [sug, setSug] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try { const { data } = await api.post(`/cases/${id}/professional-report/child-focus-suggest`); setSug(data.suggestions.filter((s) => s.suggested && !value[s.key]?.checked)); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const accept = (k) => { onChange({ ...value, [k]: { checked: true, note: "", ...(value[k] || {}) } }); setSug((x) => x.filter((s) => s.key !== k)); };
  return (
    <div data-testid="lens-child-suggest">
      <Button variant="outline" size="sm" onClick={run} disabled={busy} data-testid="lens-child-suggest-btn"><Tags className="h-4 w-4 mr-1" /> {busy ? "Analyzing…" : "Suggest categories from Joint Report"}</Button>
      {sug && (sug.length ? <div className="mt-2 flex flex-wrap gap-2" data-testid="lens-child-suggest-list">{sug.map((s) => <span key={s.key} className="flex items-center gap-1 rounded-full border border-brand-purple/40 bg-white px-2 py-0.5 text-xs" data-testid={`lens-child-suggest-${s.key}`}>{s.label} <span className="text-muted-foreground">{Math.round(s.probability * 100)}%</span><button onClick={() => accept(s.key)} className="ml-1 font-semibold text-brand-purple" data-testid={`lens-child-suggest-accept-${s.key}`}>Accept</button><button onClick={() => setSug((x) => x.filter((y) => y.key !== s.key))} className="text-muted-foreground" data-testid={`lens-child-suggest-reject-${s.key}`}>Reject</button></span>)}</div>
        : <p className="mt-2 text-xs text-muted-foreground" data-testid="lens-child-suggest-empty">No additional categories suggested.</p>)}
    </div>
  );
}

export function ParallelSummaryHelper({ id, onInsert }) {
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); try { const { data } = await api.post(`/cases/${id}/parallel-summary-draft`); setRes(data); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); } };
  return (
    <div className="rounded-md border border-brand-purple/30 bg-[#f3edfb] p-3" data-testid="lens-parallel-helper">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Parallel Parenting summary helper</p>
        <Button variant="outline" size="sm" onClick={run} disabled={busy} data-testid="lens-parallel-btn"><Sparkles className="h-4 w-4 mr-1" /> {busy ? "Drafting…" : "Draft with Claude"}</Button>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">Neutral description of the Parallel Parenting structure (written-only communication, neutral exchanges, dispute ladder) for cases with safety indicators. Review before using.</p>
      {res && (
        <div className="mt-2 rounded-md border border-amber-300 bg-white p-3 text-sm" data-testid="lens-parallel-result">
          <p className="text-[11px] font-bold text-amber-700">{res.label} · {res.model}{res.safety?.flagged ? "" : " · no safety indicators on file for these parents"}</p>
          <p className="mt-1 whitespace-pre-wrap leading-relaxed">{res.text}</p>
          <Button size="sm" variant="ghost" className="mt-2" onClick={() => onInsert(res.text)} data-testid="lens-parallel-insert-btn">Insert into Professional statement</Button>
        </div>
      )}
    </div>
  );
}

export function ResearchBase({ id, value, onChange }) {
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    setBusy(true);
    try { const { data } = await api.post(`/cases/${id}/professional-report/research-insight`); onChange(data.research_base); toast.success("Research Base updated — review before finalizing"); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const clear = async () => { try { await api.delete(`/cases/${id}/professional-report/research-insight`); onChange(null); } catch (e) { toast.error(formatApiError(e)); } };
  return (
    <aside className="rounded-md border border-teal-300 bg-white p-3" data-testid="lens-research-base">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-bold uppercase tracking-widest text-teal-700 flex items-center gap-1"><BookOpen className="h-3.5 w-3.5" /> Research Base</p>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" onClick={refresh} disabled={busy} data-testid="lens-research-base-refresh-btn">{busy ? "Fetching…" : value ? "Refresh insight" : "Fetch research insight"}</Button>
          {value && <Button size="sm" variant="ghost" onClick={clear} data-testid="lens-research-base-clear-btn">Remove</Button>}
        </div>
      </div>
      {value ? (
        <div className="mt-2 text-sm" data-testid="lens-research-base-content">
          <p className="whitespace-pre-wrap leading-relaxed">{value.text}</p>
          {value.citations?.length > 0 && <ol className="mt-2 list-decimal pl-5 text-xs" data-testid="lens-research-base-citations">{value.citations.map((c) => <li key={c.index}><a href={c.url} target="_blank" rel="noreferrer" className="text-brand-purple underline break-all">{c.url}</a></li>)}</ol>}
          <p className="mt-2 text-[11px] text-muted-foreground">Fetched {String(value.fetched_at || "").slice(0, 10)} via Perplexity {value.model}{value.zip ? ` · ZIP ${value.zip}` : ""}. Appears as a “Research Base” footer under Section 5 in the PDF. Web research for professional review — not a finding or recommendation.</p>
        </div>
      ) : <p className="mt-1 text-xs text-muted-foreground" data-testid="lens-research-base-empty">Real-time, cited research on the child-focused issues and pathways you selected (plus local resource availability near your ZIP). Fetched automatically with AI-assist draft when configured; the report is never blocked if research is unavailable.</p>}
    </aside>
  );
}

export function ResearchPanel({ onAddRow, isAdmin = false }) {
  const [cfg, setCfg] = useState(null);
  const [zip, setZip] = useState("");
  const [cat, setCat] = useState("parenting_facilitator");
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [added, setAdded] = useState({});
  const addToDirectory = async (p, i) => {
    try { await api.post("/research/providers/add", { ...p, category: res.category }); setAdded((x) => ({ ...x, [i]: true })); toast.success(`${p.name} added to the provider directory`); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { api.get("/research/config").then((r) => { setCfg(r.data); setZip(r.data.zip || ""); }).catch(() => setCfg({ configured: false, categories: [] })); }, []);
  const saveZip = async () => { try { await api.put("/me/profile/zip", { zip }); toast.success("ZIP code saved to your profile"); } catch (e) { toast.error(formatApiError(e)); } };
  const local = async () => { setBusy(true); try { if (zip && zip !== cfg.zip) await saveZip(); const { data } = await api.post("/research/local-resources", { category: cat, zip }); setRes(data); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); } };
  const ask = async () => { setBusy(true); try { const { data } = await api.post("/research/ask", { question: q }); setRes(data); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); } };
  if (!cfg) return null;
  return (
    <div className="rounded-md border border-teal-300 bg-[#e8f7f7] p-3 space-y-2" data-testid="lens-research">
      <p className="text-xs font-bold uppercase tracking-widest text-teal-700 flex items-center gap-1"><Globe className="h-3.5 w-3.5" /> Find local resources &amp; research (Perplexity)</p>
      {!cfg.configured && <p className="text-xs text-amber-700" data-testid="lens-research-unconfigured">Research helper is not configured yet — a Perplexity API key must be added by the administrator.</p>}
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs">ZIP code<input value={zip} onChange={(e) => setZip(e.target.value)} maxLength={10} className="mt-1 block h-8 w-24 rounded-md border border-input px-2 text-sm" data-testid="lens-research-zip" /></label>
        <label className="text-xs">Category<select value={cat} onChange={(e) => setCat(e.target.value)} className="mt-1 block h-8 rounded-md border border-input bg-white px-1 text-sm" data-testid="lens-research-category">{cfg.categories.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}</select></label>
        <Button size="sm" variant="outline" onClick={local} disabled={busy || !cfg.configured || !zip} data-testid="lens-research-local-btn"><ScanSearch className="h-4 w-4 mr-1" /> Find near {zip || "ZIP"}</Button>
      </div>
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. latest Texas parenting-facilitation rules" className="h-8 flex-1 rounded-md border border-input px-2 text-sm" data-testid="lens-research-question" />
        <Button size="sm" variant="outline" onClick={ask} disabled={busy || !cfg.configured || q.length < 3} data-testid="lens-research-ask-btn">{busy ? "Searching…" : "Ask"}</Button>
      </div>
      {res && (
        <div className="rounded-md border border-border bg-white p-3 text-sm" data-testid="lens-research-result">
          <p className="whitespace-pre-wrap leading-relaxed">{res.answer}</p>
          {res.providers?.length > 0 && (
            <ul className="mt-3 grid gap-2 sm:grid-cols-2" data-testid="lens-research-providers">
              {res.providers.map((p, i) => (
                <li key={i} className="rounded-md border border-teal-200 bg-[#f4fbfb] p-2 text-xs" data-testid={`lens-research-provider-${i}`}>
                  <p className="font-semibold text-sm">{p.name}</p>
                  {(p.organization || p.phone || p.website) && <p className="text-muted-foreground">{[p.organization, p.phone].filter(Boolean).join(" · ")}{p.website && <> · <a href={/^https?:/.test(p.website) ? p.website : `https://${p.website}`} target="_blank" rel="noreferrer" className="underline break-all">{p.website}</a></>}</p>}
                  {p.services && <p className="mt-0.5">{p.services}</p>}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {onAddRow && <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => onAddRow({ category: "Joint / Co-Parenting", resource: p.name, focus: [p.services, p.phone, p.website].filter(Boolean).join(" · ").slice(0, 600) })} data-testid={`lens-research-provider-row-${i}`}>Add to report</Button>}
                    {isAdmin && <Button size="sm" variant="outline" className="h-7 text-xs" disabled={!!added[i]} onClick={() => addToDirectory(p, i)} data-testid={`lens-research-provider-directory-${i}`}>{added[i] ? "In directory" : "Add to directory"}</Button>}
                  </div>
                </li>
              ))}
            </ul>
          )}
          {res.citations?.length > 0 && <ol className="mt-2 list-decimal pl-5 text-xs">{res.citations.map((c) => <li key={c.index}><a href={c.url} target="_blank" rel="noreferrer" className="text-brand-purple underline break-all">{c.url}</a></li>)}</ol>}
          <p className="mt-2 text-[11px] text-muted-foreground">{res.disclaimer}</p>
          {onAddRow && <Button size="sm" variant="ghost" className="mt-1" onClick={() => onAddRow({ category: "Joint / Co-Parenting", resource: `Local resources (${res.zip || "research"})`, focus: res.answer.slice(0, 600) })} data-testid="lens-research-add-row-btn">Add as resource row (edit before finalizing)</Button>}
        </div>
      )}
    </div>
  );
}
