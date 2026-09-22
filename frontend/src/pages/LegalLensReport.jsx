import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, Circle, Download, Eye, FileCheck2, Plus, Save, Sparkles, Trash2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { AiDraftComparison } from "@/components/AiDraftComparison";
import { ScaleTable, PathwayList } from "@/components/LensScale";

const STEPS = ["Case Information", "Safety First", "Individual Breakdown (Parent A, Parent B, Joint)", "1–10 Co-Parenting Scale", "Roadmap", "Resource & Support Options", "Regular Reassessments", "Conflict Resolution Pathways", "Certification & PDF"];
const STATUS = { draft: "Draft", under_review: "Under Review", final: "Final", submitted_to_court: "Submitted to Court" };
const Sec = ({ n, title, children, id }) => <section className="rounded-lg border border-border bg-[#f7f3fb] p-6" data-testid={`lens-${id}`}><h2 className="text-lg font-semibold text-brand-purple flex items-center gap-2">{n !== undefined && <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{n}</span>}{title}</h2><div className="mt-4 space-y-3 text-sm">{children}</div></section>;
const Field = ({ label, value, onChange, id, type = "text", big, hint }) => <label className="block text-sm"><span className="font-medium">{label}</span>{hint && <span className="block text-xs text-muted-foreground">{hint}</span>}{big ? <Textarea value={value || ""} onChange={(e) => onChange(e.target.value)} className="mt-1 min-h-[100px] bg-white" data-testid={`lens-${id}`} /> : <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid={`lens-${id}`} />}</label>;
const Radio = ({ label, options, value, onChange, id }) => <div><p className="text-sm font-medium">{label}</p><div className="mt-1 flex flex-wrap gap-3">{options.map((o) => <label key={o} className="flex items-center gap-1.5 text-sm"><input type="radio" checked={value === o} onChange={() => onChange(o)} data-testid={`lens-${id}-${o.split(/[ ,/]/)[0].toLowerCase()}`} />{o}</label>)}</div></div>;
const Rating = ({ label, value, onChange, id }) => <label className="flex items-center gap-3 text-sm"><span className="font-medium">{label}</span><input type="range" min="1" max="10" value={value || 5} onChange={(e) => onChange(Number(e.target.value))} className="flex-1 accent-brand-purple" data-testid={`lens-${id}`} /><span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-purple text-sm font-bold text-white" data-testid={`lens-${id}-value`}>{value || "–"}</span></label>;
const Band = ({ cls, joint }) => cls ? <p className="text-xs text-brand-purple font-semibold" data-testid="lens-band">Band {cls.range}: {cls.label}{joint && <span className="ml-2 rounded-full bg-brand-purple/10 px-2 py-0.5">Operating Dynamic: {cls.mode} Mode</span>}</p> : <p className="text-xs italic text-muted-foreground">Enter a 1–10 rating to see the automatic classification.</p>;

function ParentBlock({ role, rep, cls, set }) {
  const name = rep[`parent_${role}_name`] || `Parent ${role.toUpperCase()}`;
  return (
    <div className="rounded-md border border-border bg-white p-4 space-y-3" data-testid={`lens-parent-${role}`}>
      <h3 className="font-semibold text-align-green">{name}{rep[`parent_${role}_rating`] ? ` (Rated: Level ${rep[`parent_${role}_rating`]})` : ""}</h3>
      <Rating label="Rating (1–10)" value={rep[`parent_${role}_rating`]} onChange={(v) => set(`parent_${role}_rating`, v)} id={`parent-${role}-rating`} /><Band cls={cls} />
      <Field big label="What's Working Well (Strengths)" value={rep[`parent_${role}_strengths`]} onChange={(v) => set(`parent_${role}_strengths`, v)} id={`parent-${role}-strengths`} />
      <Field big label="Real-World Example (Gaps)" value={rep[`parent_${role}_gaps`]} onChange={(v) => set(`parent_${role}_gaps`, v)} id={`parent-${role}-gaps`} />
      <Field big label="Key Growth Areas" hint="One per line — three focused, behavioral goals (e.g. “Focus on sending calm, strictly factual messages…”)." value={rep[`parent_${role}_growth`]} onChange={(v) => set(`parent_${role}_growth`, v)} id={`parent-${role}-growth`} />
      <Field big label="Professional Notes (PARENT-REPORTED INFORMATION summarized by the professional)" value={rep[`parent_${role}_notes`]} onChange={(v) => set(`parent_${role}_notes`, v)} id={`parent-${role}-notes`} />
    </div>
  );
}

function ResourceRows({ rows = [], lib, onChange }) {
  const upd = (i, k, val) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: val } : r)));
  const add = (r = { category: lib.resource_categories[0], resource: "", focus: "" }) => onChange([...rows, r]);
  const cat = (p) => (/education/i.test(p.specialty) ? "Educational Assessment" : /children in the middle/i.test(p.specialty) ? "Parent Education" : /options|forensic|facilitat/i.test(p.specialty) ? "Clinical & Forensics" : "Joint / Co-Parenting");
  return (
    <div className="space-y-2" data-testid="lens-resource-rows">
      <div className="hidden sm:grid grid-cols-[1.1fr_1.4fr_2fr_auto] gap-2 text-xs font-bold uppercase tracking-widest text-muted-foreground"><span>Category</span><span>Recommended Resource / Specialist</span><span>Service Focus &amp; Scope</span><span /></div>
      {rows.map((r, i) => (
        <div key={i} className="grid gap-2 sm:grid-cols-[1.1fr_1.4fr_2fr_auto] rounded-md border border-border bg-white p-2" data-testid={`lens-resource-row-${i}`}>
          <select value={r.category} onChange={(e) => upd(i, "category", e.target.value)} className="h-8 rounded-md border border-input bg-white px-1 text-xs" data-testid={`lens-resource-category-${i}`}>{lib.resource_categories.map((c) => <option key={c}>{c}</option>)}</select>
          <input value={r.resource} onChange={(e) => upd(i, "resource", e.target.value)} className="h-8 rounded-md border border-input px-2 text-sm" data-testid={`lens-resource-name-${i}`} />
          <input value={r.focus} onChange={(e) => upd(i, "focus", e.target.value)} className="h-8 rounded-md border border-input px-2 text-sm" data-testid={`lens-resource-focus-${i}`} />
          <button onClick={() => onChange(rows.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-destructive" aria-label="Remove row" data-testid={`lens-resource-remove-${i}`}><Trash2 className="h-4 w-4" /></button>
        </div>
      ))}
      <div className="flex flex-wrap gap-2 pt-1">
        <Button size="sm" variant="outline" onClick={() => add()} data-testid="lens-resource-add"><Plus className="h-4 w-4 mr-1" /> Add row</Button>
        {(lib.providers || []).map((p) => <Button key={p.id} size="sm" variant="ghost" onClick={() => add({ category: cat(p), resource: p.label, focus: p.contact })} data-testid={`lens-resource-add-provider-${p.id}`}>+ {p.name}</Button>)}
      </div>
    </div>
  );
}

export default function LegalLensReport() {
  const { id } = useParams();
  const [v, setV] = useState(null);
  const [rep, setRep] = useState({});
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(false);
  const [model, setModel] = useState("gemini");
  const [aiInfo, setAiInfo] = useState(null);
  const aiDraft = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/cases/${id}/professional-report/ai-draft`, { fields: rep, model });
      const empty = Object.keys(data.fields).filter((k) => !(rep[k] || "").trim());
      const keys = empty.length ? empty : Object.keys(data.fields);
      setRep((r) => ({ ...r, ...Object.fromEntries(keys.map((k) => [k, data.fields[k]])), ai_drafts: data.ai_drafts }));
      setAiInfo(data);
      toast.success(`${data.model}${data.source === "rule_based" ? " unavailable — rule-based" : ""} draft filled ${keys.length} section${keys.length === 1 ? "" : "s"}. Review and edit before finalizing.`);
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const set = (k, val) => setRep((r) => ({ ...r, [k]: val }));
  const apply = (data) => { setV(data); setRep(data.report); };
  useEffect(() => { api.get(`/cases/${id}/professional-report`).then((r) => apply(r.data)).catch((e) => toast.error(formatApiError(e))); }, [id]);
  useEffect(() => { if (!v) return; const t = setTimeout(() => api.put(`/cases/${id}/professional-report`, { fields: { parent_a_rating: rep.parent_a_rating, parent_b_rating: rep.parent_b_rating, joint_rating: rep.joint_rating } }).then((r) => setV((x) => ({ ...x, classification: r.data.classification }))).catch(() => {}), 400); return () => clearTimeout(t); }, [rep.parent_a_rating, rep.parent_b_rating, rep.joint_rating]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async (status) => { setBusy(true); try { const { data } = await api.put(`/cases/${id}/professional-report`, { fields: rep, ...(status ? { status } : {}) }); apply(data); toast.success(status ? `Report marked ${STATUS[status]}` : "Draft saved"); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); } };
  if (!v) return <div className="min-h-screen bg-white" data-testid="lens-loading" />;
  const { classification: cls, library: lib, notes, readiness } = v;
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/cases/${id}/professional-report/pdf`;
  const risk = rep.risk_screening || {};
  const setRisk = (k, patch) => set("risk_screening", { ...risk, [k]: { level: "Not assessed", note: "", ...(risk[k] || {}), ...patch } });
  const actions = (top) => (
    <div className="flex flex-wrap gap-2" data-testid={top ? "lens-actions" : "lens-actions-bottom"}>
      <Button variant="outline" size="sm" onClick={() => save()} disabled={busy} data-testid="lens-save-btn"><Save className="h-4 w-4 mr-1" /> Save Draft</Button>
      <Button variant="outline" size="sm" onClick={async () => { await save(); setPreview(!preview); }} disabled={busy} data-testid="lens-preview-btn"><Eye className="h-4 w-4 mr-1" /> {preview ? "Back to Editor" : "Preview Report"}</Button>
      <Button variant="outline" size="sm" asChild data-testid="lens-pdf-btn"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> Print / Save as PDF</a></Button>
      <Button size="sm" onClick={() => save("final")} disabled={busy || !rep.signature_name} data-testid="lens-finalize-btn"><FileCheck2 className="h-4 w-4 mr-1" /> Finalize Report</Button>
      <select value={rep.status} onChange={(e) => save(e.target.value)} className="h-9 rounded-md border border-input bg-white px-2 text-sm" data-testid="lens-status-select">{lib.statuses.map((s) => <option key={s} value={s}>{STATUS[s]}</option>)}</select>
      {top && rep.status !== "final" && rep.status !== "submitted_to_court" && <span className="flex items-center gap-1 rounded-md border border-brand-purple/30 bg-brand-purple/5 px-2" data-testid="lens-ai-block">
        <select value={model} onChange={(e) => setModel(e.target.value)} className="h-7 rounded-md border border-input bg-white px-1 text-xs" data-testid="lens-ai-model-select">{(lib.ai_models || []).map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}</select>
        <Button variant="ghost" size="sm" onClick={aiDraft} disabled={busy} data-testid="lens-ai-draft-btn"><Sparkles className="h-4 w-4 mr-1" /> AI-assist draft</Button>
      </span>}
    </div>
  );
  const aiNotice = aiInfo && <p className="rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs" data-testid="lens-ai-notice"><strong>{aiInfo.label}</strong> — generated with {aiInfo.model}{aiInfo.source === "rule_based" ? " (model unavailable; rule-based text used)" : ""}. The professional must review, edit and certify every AI-assisted section before finalizing. AI text makes no legal conclusion or custody recommendation.</p>;
  return (
    <div className="min-h-screen bg-white" data-testid="lens-page">
      <header className="border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2"><Link to={`/joint/${id}`} className="flex items-center gap-1.5 text-sm text-muted-foreground" data-testid="lens-back"><ArrowLeft className="h-4 w-4" /> Back to Case</Link><BrandLogo size="text-xl" /><span className="rounded-full bg-brand-purple/10 px-3 py-1 text-xs font-semibold text-brand-purple" data-testid="lens-status">{STATUS[rep.status]}</span></div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5">
        <div className="border-b-2 border-brand-purple pb-3">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-brand-purple" data-testid="lens-title">SA CoParents Align Professional Evaluation Report</h1>
          <p className="text-sm text-muted-foreground mt-2"><strong className="text-foreground">Platform:</strong> sacoparentsalign.com · <strong className="text-foreground">Focus:</strong> Comprehensive 1–10 Scale Analysis (Joint &amp; Individual Behaviors), Stage-Specific Profiles, Resources &amp; Actionable Roadmap</p>
        </div>
        <ol className="flex flex-wrap gap-1 text-[11px]" data-testid="lens-steps">{STEPS.map((s, i) => <li key={s} className="rounded-full border border-brand-purple/30 px-2 py-0.5 text-brand-purple">{i + 1}. {s}</li>)}</ol>
        <ul className="flex flex-wrap gap-3 text-xs" data-testid="lens-readiness">{readiness.map((r) => <li key={r.key} className="flex items-center gap-1">{r.done ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}{r.label}{r.na && !r.done ? " (N/A)" : ""}</li>)}</ul>
        {actions(true)}
        {aiNotice}
        <AiDraftComparison drafts={rep.ai_drafts} rep={rep} />
        {preview ? <iframe title="Report preview" src={pdf} className="h-[80vh] w-full rounded-lg border border-border" data-testid="lens-preview-frame" /> : (
          <>
            <Sec title="What This Report Covers" id="intro"><p className="text-sm leading-relaxed" data-testid="lens-intro">{notes.intro}</p></Sec>
            <Sec title="Case Information" id="case"><div className="grid gap-3 sm:grid-cols-3">{[["matter_name", "Case / Matter Name"], ["court_county", "Court / County"], ["cause_number", "Cause Number"], ["professional_role", "Professional Role"], ["parent_a_name", "Parent A Name"], ["parent_b_name", "Parent B Name"]].map(([k, l]) => <Field key={k} label={l} value={rep[k]} onChange={(val) => set(k, val)} id={k} />)}<label className="block text-sm"><span className="font-medium">Case ID</span><input readOnly value={v.case.case_code || ""} className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm" data-testid="lens-case-id" /></label><label className="block text-sm"><span className="font-medium">Professional Name</span><input readOnly value={rep.professional_name || ""} className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm" data-testid="lens-professional-name" /></label><Field label="Report Date" type="date" value={rep.report_date} onChange={(val) => set("report_date", val)} id="report_date" /></div></Sec>
            <Sec n={1} title="Safety First: Checking for Domestic Violence & IPV Risks" id="safety">
              <p className="text-sm">Before evaluating co-parenting scores or suggesting joint meetings, we screen for <strong>Intimate Partner Violence (IPV) and coercive control</strong>.</p>
              <p className="rounded-r-md border-l-4 border-amber-500 bg-amber-50 p-3 text-xs" data-testid="lens-safety-alert">{notes.alert}</p>
              <div className="grid gap-3 sm:grid-cols-2"><Radio label="Parent A Family Violence Assessment" options={lib.receipt_options} value={rep.fv_a_received} onChange={(val) => set("fv_a_received", val)} id="fv-a" /><Radio label="Parent B Family Violence Assessment" options={lib.receipt_options} value={rep.fv_b_received} onChange={(val) => set("fv_b_received", val)} id="fv-b" /></div>
              <p className="text-xs font-semibold" data-testid="lens-fv-both">{rep.fv_a_received === "Received" && rep.fv_b_received === "Received" ? "✓ Both Assessments Received" : "Both assessments not yet received"}</p>
              <h3 className="font-semibold text-align-green">Risk Screening Summary</h3>
              <div className="space-y-2" data-testid="lens-risk-grid">{lib.risk_categories.map(([k, label, hint]) => (
                <div key={k} className="grid gap-2 sm:grid-cols-[1.2fr_1fr_2fr] items-start rounded-md border border-border bg-white p-2">
                  <div><p className="text-sm font-semibold">{label}</p><p className="text-xs text-muted-foreground">{hint}</p></div>
                  <select value={risk[k]?.level || "Not assessed"} onChange={(e) => setRisk(k, { level: e.target.value })} className="h-8 rounded-md border border-input bg-white px-1 text-sm" data-testid={`lens-risk-${k}`}>{lib.risk_levels.map((l) => <option key={l}>{l}</option>)}</select>
                  <input value={risk[k]?.note || ""} onChange={(e) => setRisk(k, { note: e.target.value })} placeholder="Basis / observation (screening summary, not a finding)" className="h-8 rounded-md border border-input px-2 text-sm" data-testid={`lens-risk-${k}-note`} />
                </div>))}</div>
              <Radio label="Joint Process Appropriate?" options={lib.joint_process_options} value={rep.joint_process_appropriate} onChange={(val) => set("joint_process_appropriate", val)} id="joint-process" />
              <Field big label="Safety Notes / Safeguards" value={rep.safety_notes} onChange={(val) => set("safety_notes", val)} id="safety_notes" />
              <Field big label="Takeaway" hint="e.g. whether an emergency safety override is required and whether direct face-to-face negotiation is a fit right now." value={rep.safety_takeaway} onChange={(val) => set("safety_takeaway", val)} id="safety_takeaway" />
              <p className="text-xs italic" data-testid="lens-safety-note">{notes.safety}</p>
            </Sec>
            <Sec n={2} title="Detailed Individual Breakdown for Parent A & Parent B" id="individual">
              <ParentBlock role="a" rep={rep} cls={cls.parent_a} set={set} /><ParentBlock role="b" rep={rep} cls={cls.parent_b} set={set} />
              <div className="rounded-md border border-border bg-white p-4 space-y-3" data-testid="lens-joint">
                <h3 className="font-semibold text-align-green">Joint Dynamic Summary{rep.joint_rating ? ` (Rated: Level ${rep.joint_rating})` : ""}</h3>
                <Rating label="Joint Co-Parenting Rating (1–10)" value={rep.joint_rating} onChange={(val) => set("joint_rating", val)} id="joint-rating" /><Band cls={cls.joint} joint />
                <div className="grid gap-3 sm:grid-cols-2"><Field big label="Where the Parents Do Well Together" value={rep.joint_strengths} onChange={(val) => set("joint_strengths", val)} id="joint_strengths" /><Field big label="Where the Parents Struggle Together" value={rep.joint_gaps} onChange={(val) => set("joint_gaps", val)} id="joint_gaps" /></div>
                <Field big label="Summary" value={rep.joint_notes} onChange={(val) => set("joint_notes", val)} id="joint_notes" />
              </div>
            </Sec>
            <Sec n={3} title="Comprehensive 1–10 Co-Parenting Scale: Joint & Individual Behaviors" id="scale"><ScaleTable scale={lib.scale_table} cls={cls} rep={rep} /></Sec>
            <Sec n={4} title="Post-Rating Roadmap: Short-Term & Long-Term Goals" id="roadmap">
              <Field big label="A. Short-Term Goals (Next 30 to 90 Days)" hint="One goal per line, as “Title: concrete action”." value={rep.short_term_goals} onChange={(val) => set("short_term_goals", val)} id="short_term_goals" />
              <Field big label="B. Long-Term Goals (6 to 12 Months)" hint="One goal per line." value={rep.long_term_goals} onChange={(val) => set("long_term_goals", val)} id="long_term_goals" />
            </Sec>
            <Sec n={5} title="Resource & Support Options" id="resources"><ResourceRows rows={rep.resource_rows} lib={lib} onChange={(rows) => set("resource_rows", rows)} /></Sec>
            <Sec n={6} title="Checking In: Regular Reassessments" id="reassess">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm"><span className="font-medium">Reassessment interval</span><select value={rep.reassess_interval || ""} onChange={(e) => set("reassess_interval", e.target.value)} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid="lens-reassess_interval">{lib.reassess_intervals.map((o) => <option key={o}>{o}</option>)}</select></label>
                <Field label="Next Review / Reassessment Date" type="date" value={rep.next_review_date} onChange={(val) => set("next_review_date", val)} id="next_review_date" />
              </div>
              <Field big label="When Score Moves Up" value={rep.reassess_up} onChange={(val) => set("reassess_up", val)} id="reassess_up" />
              <Field big label="When Score Drops" value={rep.reassess_down} onChange={(val) => set("reassess_down", val)} id="reassess_down" />
            </Sec>
            <Sec n={7} title="Conflict Resolution Pathways (Levels 1–10)" id="conflict">
              <PathwayList pathways={lib.pathways} rating={rep.joint_rating} recommended={cls.joint?.pathway?.key} chosen={rep.conflict_pathway} onChoose={(k) => set("conflict_pathway", k)} />
              <Field big label="Rationale / Recommended Structure" value={rep.conflict_management_rationale} onChange={(val) => set("conflict_management_rationale", val)} id="conflict_management_rationale" />
              <p className="text-xs italic" data-testid="lens-rating-note">{notes.rating}</p>
            </Sec>
            <Sec title="Professional Certification" id="summary">
              <p className="text-xs italic">This report reflects the professional's review of the individual assessments, safety screenings and Joint Report. It contains no custody recommendation, credibility determination, diagnosis or legal conclusion.</p>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Professional Signature Name" value={rep.signature_name} onChange={(val) => set("signature_name", val)} id="signature_name" /><Field label="Professional Title" value={rep.professional_title} onChange={(val) => set("professional_title", val)} id="professional_title" /></div>
              {rep.finalized_at && <p className="text-xs text-align-green font-semibold" data-testid="lens-finalized">Date finalized: {rep.finalized_at.slice(0, 10)}</p>}
            </Sec>
            {actions(false)}
          </>
        )}
        <p className="text-center text-xs text-brand-purple font-semibold">{notes.tagline}</p>
      </main>
    </div>
  );
}
