import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Download, Eye, FileCheck2, RefreshCw, Save, Sparkles } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { LegalGeneratedSections, LegalReadOnlyTail, Sec } from "@/components/LegalReportSections";

const LENS = [["observations", "Professional Observations"], ["further_attention", "Issues Requiring Attention"], ["alignment_areas", "Areas of Existing Agreement"],
  ["partial_alignment", "Areas Appropriate for Further Agreement Building"], ["procedural_considerations", "Procedural Considerations"], ["professional_comments", "Other Professional Comments"]];
const STATUS = { not_started: "Not Started", draft: "Draft", professional_review: "Professional Review", finalized: "Finalized" };
const CERT_FIELDS = [["certified_name", "Professional name *"], ["certified_date", "Date *"], ["title", "Professional title"], ["bar_number", "Bar number"], ["organization", "Firm / organization"], ["email", "Email"], ["phone", "Phone"]];

function Availability({ rows }) {
  const tone = (s) => (s === "Complete" || s === "Available" ? "text-align-green" : s === "Not Applicable" || s === "None" ? "text-muted-foreground" : "text-amber-700");
  return (
    <div className="grid gap-1.5 sm:grid-cols-2" data-testid="legal-availability">
      {rows.map((r) => <div key={r.key} className="flex justify-between gap-3 rounded-md border border-border px-3 py-2 text-sm" data-testid={`legal-avail-${r.key}`}><span>{r.label}</span><span className={`font-semibold ${tone(r.status)}`}>{r.status}</span></div>)}
    </div>
  );
}

export default function LegalReport() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  const [st, setSt] = useState({});
  const [custom, setCustom] = useState("");
  const [cert, setCert] = useState({ certified: false, certified_name: "", certified_date: new Date().toISOString().slice(0, 10), title: "", bar_number: "", organization: "", email: "", phone: "" });
  const [busy, setBusy] = useState("");
  const [preview, setPreview] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const apply = (data) => { setD(data); setSt(data.report || {}); };
  useEffect(() => { api.get(`/cases/${id}/professional-legal-report`).then((r) => apply(r.data)).catch((e) => toast.error(formatApiError(e))); }, [id]);
  const run = async (label, fn) => { setBusy(label); try { await fn(); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(""); } };
  const generate = (regenerate) => run("generate", async () => { const { data } = await api.post(`/cases/${id}/professional-legal-report/generate`, { regenerate }); apply(data); toast.success(regenerate ? "Draft regenerated" : "Draft generated — review every section before finalizing"); });
  const fields = () => ({ observations: st.observations || "", further_attention: st.further_attention || "", alignment_areas: st.alignment_areas || "", partial_alignment: st.partial_alignment || "", procedural_considerations: st.procedural_considerations || "", professional_comments: st.professional_comments || "",
    options_resources: st.options_resources || [], options_custom: st.options_custom || [], conflict_resolution_paths: st.conflict_resolution_paths || [], conflict_resolution_explanation: st.conflict_resolution_explanation || "" });
  const save = () => run("save", async () => { const { data } = await api.patch(`/professional-legal-reports/${id}`, { fields: fields() }); apply(data); toast.success("Draft saved"); });
  const doPreview = () => run("preview", async () => { await api.patch(`/professional-legal-reports/${id}`, { fields: fields() }); await api.post(`/professional-legal-reports/${id}/preview`); setPreview(true); });
  const finalize = () => run("finalize", async () => { await api.patch(`/professional-legal-reports/${id}`, { fields: fields() }); const { data } = await api.post(`/professional-legal-reports/${id}/finalize`, cert); apply(data); setConfirm(false); setPreview(true); toast.success(`Finalized — version ${data.report.legal_version}`); });
  const toggle = (k, item) => setSt({ ...st, [k]: (st[k] || []).includes(item) ? st[k].filter((x) => x !== item) : [...(st[k] || []), item] });
  if (!d) return <div className="min-h-screen bg-background" data-testid="legal-report-loading" />;
  const started = !!st.legal_draft;
  const finalized = d.status === "finalized";
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/professional-legal-reports/${id}/pdf`;
  return (
    <div className="min-h-screen bg-background" data-testid="legal-report-page">
      <header className="bg-white border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2">
        <Link to={`/joint/${id}`} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground" data-testid="legal-report-back"><ArrowLeft className="h-4 w-4" /> Back to Case</Link>
        <div className="hidden sm:block"><BrandLogo size="text-xl" /></div>
        <span className="rounded-full border border-border px-3 py-1 text-xs font-semibold" data-testid="legal-report-status-pill">{STATUS[d.status]}</span>
      </div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Legal Lens</p>
          <h1 className="text-3xl sm:text-4xl font-extrabold mt-1" data-testid="legal-report-title">{started ? "Professional Legal Report" : "Create Professional Legal Report"}</h1>
          <p className="text-sm text-muted-foreground mt-2 max-w-3xl">SA CoParents Align organizes available parent-reported information for professional review. The generated report is a draft and must be independently reviewed and approved by the professional.</p>
        </div>

        <Sec n="✓" title="Information Available for Review" testId="legal-availability-section">
          <Availability rows={d.availability} />
          <p className="text-xs text-muted-foreground">Restricted family-violence information is only shown to professionals with permission to view it.</p>
          {!started && <Button onClick={() => generate(false)} disabled={busy === "generate"} data-testid="legal-generate-btn"><Sparkles className="h-4 w-4 mr-1" /> {busy === "generate" ? "Generating…" : "Generate Draft Professional Legal Report"}</Button>}
        </Sec>

        {started && !preview && (
          <>
            <LegalGeneratedSections data={d} />
            <Sec n={8} title="Professional Legal Lens" testId="legal-lens-section">
              <p className="italic text-muted-foreground">The following section is reserved for the reviewing professional's independent observations and analysis.</p>
              {st.ai_generated_content && <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900" data-testid="legal-ai-label">{d.ai_label} · source: {st.ai_generated_content.source === "ai" ? "AI (GPT-5.4 mini)" : "rule-based system draft"} · {st.ai_generated_content.generated_at?.slice(0, 16).replace("T", " ")}</p>}
              {LENS.map(([k, t]) => <label key={k} className="block"><span className="text-sm font-medium">{t}</span>{k === "professional_comments" && <span className="block text-xs text-muted-foreground">Your own words only — never AI-prefilled.</span>}<Textarea value={st[k] || ""} onChange={(e) => setSt({ ...st, [k]: e.target.value })} className="mt-1 min-h-[96px]" data-testid={`legal-lens-${k}`} /></label>)}
            </Sec>
            <Sec n={9} title="Options and Resources" testId="legal-options-section">
              <p className="text-xs text-muted-foreground">Identify options for consideration. None is stated as legally required unless an entered court order provides otherwise.</p>
              <ul className="grid gap-1 sm:grid-cols-2">{d.options_library.map((o) => <li key={o}><label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={(st.options_resources || []).includes(o)} onChange={() => toggle("options_resources", o)} data-testid="legal-option" /><span>{o}</span></label></li>)}</ul>
              {(st.options_custom || []).map((o, i) => <p key={i} className="flex items-center gap-2 text-sm" data-testid="legal-option-custom"><span className="rounded bg-brand-purple/10 px-1 text-[10px] font-bold text-brand-purple">OWN</span>{o}<button type="button" className="text-xs text-muted-foreground underline" onClick={() => setSt({ ...st, options_custom: st.options_custom.filter((_, j) => j !== i) })}>remove</button></p>)}
              <div className="flex gap-2"><input value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="Add another option or resource…" className="h-9 flex-1 rounded-md border border-input bg-white px-2 text-sm" data-testid="legal-option-custom-input" /><Button type="button" variant="outline" size="sm" onClick={() => { if (custom.trim()) { setSt({ ...st, options_custom: [...(st.options_custom || []), custom.trim()] }); setCustom(""); } }} data-testid="legal-option-custom-add">Add</Button></div>
            </Sec>
            <Sec n={10} title="Possible Conflict-Resolution Path" testId="legal-paths-section">
              <ul className="grid gap-1 sm:grid-cols-2">{d.paths.map((p) => <li key={p}><label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={(st.conflict_resolution_paths || []).includes(p)} onChange={() => toggle("conflict_resolution_paths", p)} data-testid="legal-path" /><span>{p}</span></label></li>)}</ul>
              <label className="block"><span className="text-sm font-medium">Professional Explanation</span><Textarea value={st.conflict_resolution_explanation || ""} onChange={(e) => setSt({ ...st, conflict_resolution_explanation: e.target.value })} className="mt-1 min-h-[96px]" data-testid="legal-path-explanation" /></label>
            </Sec>
            {d.safety_notice_text && <Sec n={11} title="Safety Considerations" testId="legal-safety-section"><p className="rounded-md border-l-4 border-red-600 bg-red-50 p-3 text-sm">{d.safety_notice_text}</p></Sec>}
            <Sec n={d.safety_notice_text ? 12 : 11} title="Professional Certification" testId="legal-cert-section">
              <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={cert.certified} onChange={(e) => setCert({ ...cert, certified: e.target.checked })} data-testid="legal-cert-checkbox" /><span>{d.certification_text}</span></label>
              <div className="grid gap-2 sm:grid-cols-2">{CERT_FIELDS.map(([k, l]) => <label key={k} className="block text-xs font-medium">{l}<input type={k === "certified_date" ? "date" : "text"} value={cert[k]} onChange={(e) => setCert({ ...cert, [k]: e.target.value })} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm font-normal" data-testid={`legal-cert-${k}`} /></label>)}</div>
              {st.professional_certified && <p className="text-xs text-align-green font-semibold" data-testid="legal-cert-done">Certified by {st.professional_certified_name} on {st.professional_certified_date} · version {st.legal_version}</p>}
            </Sec>
          </>
        )}

        {started && preview && (
          <div className="space-y-5" data-testid="legal-preview">
            <div className="rounded-md border border-border bg-white p-3 text-sm flex items-center justify-between"><span>Preview — {finalized ? `finalized version ${st.legal_version}` : "draft, not yet certified"}</span><Button size="sm" variant="outline" onClick={() => setPreview(false)} data-testid="legal-edit-btn">Edit Report</Button></div>
            <LegalGeneratedSections data={d} /><LegalReadOnlyTail data={d} />
          </div>
        )}

        {started && (
          <div className="sticky bottom-3 rounded-lg border border-border bg-white/95 backdrop-blur p-3 flex flex-wrap gap-2" data-testid="legal-actions">
            <Button variant="outline" onClick={save} disabled={!!busy} data-testid="legal-save-btn"><Save className="h-4 w-4 mr-1" /> Save Draft</Button>
            {preview ? <Button variant="outline" onClick={() => setPreview(false)} data-testid="legal-edit-btn-2">Edit Report</Button> : <Button variant="outline" onClick={doPreview} disabled={!!busy} data-testid="legal-preview-btn"><Eye className="h-4 w-4 mr-1" /> Preview Report</Button>}
            <Button variant="outline" onClick={() => generate(true)} disabled={!!busy} data-testid="legal-regenerate-btn"><RefreshCw className="h-4 w-4 mr-1" /> Regenerate Draft</Button>
            <Button onClick={() => setConfirm(true)} disabled={!!busy || !cert.certified || !cert.certified_name.trim()} data-testid="legal-finalize-btn"><FileCheck2 className="h-4 w-4 mr-1" /> Finalize Report</Button>
            <Button variant={finalized ? "default" : "outline"} asChild data-testid="legal-pdf-btn"><a href={pdf} download>{finalized ? <><Download className="h-4 w-4 mr-1" /> Export Final PDF</> : <><Download className="h-4 w-4 mr-1" /> Export Draft PDF (watermarked)</>}</a></Button>
            {d.versions?.length > 0 && <span className="self-center text-xs text-muted-foreground" data-testid="legal-versions">{d.versions.length} finalized version{d.versions.length > 1 ? "s" : ""}</span>}
          </div>
        )}

        {confirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" data-testid="legal-finalize-dialog">
            <div className="max-w-md rounded-lg bg-white p-6 shadow-xl">
              <p className="font-semibold">Finalize Professional Legal Report?</p>
              <p className="mt-2 text-sm text-muted-foreground">Finalizing this report will create a dated professional version of the report. Parent-reported statements remain identified as parent-reported information. Are you ready to finalize?</p>
              <div className="mt-4 flex justify-end gap-2"><Button variant="outline" onClick={() => setConfirm(false)} data-testid="legal-finalize-cancel">Cancel</Button><Button onClick={finalize} disabled={busy === "finalize"} data-testid="legal-finalize-confirm">Finalize Professional Report</Button></div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
