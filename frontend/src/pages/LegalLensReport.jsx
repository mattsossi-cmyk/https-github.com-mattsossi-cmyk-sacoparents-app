import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, Circle, Download, Eye, FileCheck2, Plus, Save, Sparkles, Trash2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { AiDraftComparison } from "@/components/AiDraftComparison";
import { IndividualScaleTable, JointScaleTable, growthOf } from "@/components/LensScale";
import { WorkflowGuide } from "@/components/WorkflowGuide";
import { SectionGuide, WalkthroughOverview, useWalkthrough } from "@/components/LensWalkthrough";
import { REPORT_STEPS, ReportPrinciple, ChildFocusList, PathwayPicker, ReportHeader, ReportDisclaimer, AlignmentStatusGrid, LensSec } from "@/components/LensSections";
import { ReportCover } from "@/components/ReportCover";
import { ProfileContactForm } from "@/components/ProfileContactForm";
import { SignatureCapture } from "@/components/SignatureCapture";
import { AlignAssistant } from "@/components/AlignAssistant";
import { ImportedScreening } from "@/components/ImportedScreening";
import { SixQuestions, SourceLegend, StatementDivider } from "@/components/ReportFraming";
import { GrowthProgress } from "@/components/CourtLegalSummary";
import { AiPrivacyWarning } from "@/components/AiPrivacyWarning";
import { NeutralityCheck, ChildFocusSuggest, ParallelSummaryHelper, ResearchPanel, ResearchBase } from "@/components/LensAiTools";

const STEPS = REPORT_STEPS;
const STATUS = { draft: "Draft", under_review: "Under Review", final: "Final", submitted_to_court: "Submitted to Court" };
const GUIDE_SEC = { 1: "case", 2: "snapshot", 3: "parent-a", 4: "parent-b", 5: "joint", 6: "child", 7: "resources", 8: "conflict", 9: "legal", 10: "summary", 11: "court-summary" };
const GUIDE_FIELDS = { 1: ["matter_name", "court_county"], 2: ["parent_a_rating", "parent_b_rating", "joint_rating"], 3: ["parent_a_strengths", "parent_a_gaps"], 4: ["parent_b_strengths", "parent_b_gaps"], 5: ["alignment_agreements", "joint_notes"], 6: ["child_focus"], 7: ["resource_rows"], 8: ["conflict_pathways", "pathway_rationale"], 9: ["agreement_building_opportunities", "issues_requiring_attention"], 10: ["professional_summary", "short_term_goals"], 11: ["court_summary_text"] };
const Sec = ({ n, title, children, id, guides }) => <LensSec n={n} title={title} id={id}>{guides && <SectionGuide ns={[n]} guides={guides} />}{children}</LensSec>;
const FieldBase = ({ label, value, onChange, id, type = "text", big, hint, badge }) => <label className="block text-sm"><span className="font-medium">{label}</span>{badge}{hint && <span className="block text-xs text-muted-foreground">{hint}</span>}{big ? <Textarea value={value || ""} onChange={(e) => onChange(e.target.value)} className={`mt-1 min-h-[100px] bg-white ${badge ? "border-align-yellow ring-1 ring-align-yellow/60" : ""}`} data-testid={`lens-${id}`} /> : <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid={`lens-${id}`} />}</label>;
const DraftBadge = ({ id, onAccept }) => <span className="ml-2 inline-flex items-center gap-1.5 rounded-full bg-align-yellow/25 px-2 py-0.5 text-[11px] font-semibold text-yellow-900 align-middle" data-testid={`lens-draft-badge-${id}`}><Sparkles className="h-3 w-3" /> AI-assisted draft — needs your review<button type="button" onClick={onAccept} className="ml-1 rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-brand-purple hover:bg-brand-purple hover:text-white" data-testid={`lens-draft-accept-${id}`}>Accept</button></span>;
const Radio = ({ label, options, value, onChange, id }) => <div><p className="text-sm font-medium">{label}</p><div className="mt-1 flex flex-wrap gap-3">{options.map((o) => <label key={o} className="flex items-center gap-1.5 text-sm"><input type="radio" checked={value === o} onChange={() => onChange(o)} data-testid={`lens-${id}-${o.split(/[ ,/]/)[0].toLowerCase()}`} />{o}</label>)}</div></div>;
const Rating = ({ label, value, onChange, id }) => <label className="flex items-center gap-3 text-sm"><span className="font-medium">{label}</span><input type="range" min="1" max="10" value={value || 5} onChange={(e) => onChange(Number(e.target.value))} className="flex-1 accent-brand-purple" data-testid={`lens-${id}`} /><span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-purple text-sm font-bold text-white" data-testid={`lens-${id}-value`}>{value || "–"}</span></label>;
const Band = ({ cls, joint }) => cls ? <p className="text-xs text-brand-purple font-semibold" data-testid="lens-band">Band {cls.range}: {cls.label}{joint && <span className="ml-2 rounded-full bg-brand-purple/10 px-2 py-0.5">Operating Dynamic: {cls.mode} Mode</span>}</p> : <p className="text-xs italic text-muted-foreground">Enter a 1–10 rating to see the automatic classification.</p>;

function GrowthTracker({ role, rep, set }) {
  const lines = (rep[`parent_${role}_growth`] || "").split("\n").map((s) => s.trim()).filter(Boolean);
  if (!lines.length) return null;
  const status = (rep.growth_status || {})[role] || {};
  const met = lines.filter((l) => status[l]).length;
  const toggle = (l) => set("growth_status", { ...(rep.growth_status || {}), [role]: { ...status, [l]: !status[l] } });
  return (
    <div className="rounded-md border border-align-green/40 bg-align-green/5 p-3" data-testid={`lens-growth-tracker-${role}`}>
      <p className="text-xs font-bold uppercase tracking-widest text-align-green">Met at reassessment — {met} of {lines.length}</p>
      <GrowthProgress met={met} total={lines.length} testId={`lens-growth-progress-${role}`} />
      <ul className="mt-1 space-y-1">{lines.map((l, i) => <li key={l}><label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={!!status[l]} onChange={() => toggle(l)} data-testid={`lens-growth-met-${role}-${i}`} /><span className={status[l] ? "line-through decoration-align-green/60" : ""}>{l}</span></label></li>)}</ul>
      <p className="mt-1 text-[11px] text-muted-foreground">Tick a goal once it is consistently observed; the met/total count is frozen with each court submission so the level history shows what actually improved.</p>
    </div>
  );
}

function ParentBlock({ role, rep, cls, set, Field = FieldBase }) {
  const name = rep[`parent_${role}_name`] || `Parent ${role.toUpperCase()}`;
  return (
    <div className="rounded-md border border-border bg-white p-4 space-y-3" data-testid={`lens-parent-${role}`}>
      <h3 className="font-semibold text-align-green">{name}{rep[`parent_${role}_rating`] ? ` (Rated: Level ${rep[`parent_${role}_rating`]})` : ""}</h3>
      <Rating label="Rating (1–10)" value={rep[`parent_${role}_rating`]} onChange={(v) => set(`parent_${role}_rating`, v)} id={`parent-${role}-rating`} /><Band cls={cls} />
      <Field big label="What's Working Well (Strengths)" value={rep[`parent_${role}_strengths`]} onChange={(v) => set(`parent_${role}_strengths`, v)} id={`parent-${role}-strengths`} />
      <Field big label="Real-World Example (Gaps)" value={rep[`parent_${role}_gaps`]} onChange={(v) => set(`parent_${role}_gaps`, v)} id={`parent-${role}-gaps`} />
      <Field big label="Key Growth Areas" hint="One per line — three focused, behavioral goals (e.g. “Focus on sending calm, strictly factual messages…”)." value={rep[`parent_${role}_growth`]} onChange={(v) => set(`parent_${role}_growth`, v)} id={`parent-${role}-growth`} />
      <GrowthTracker role={role} rep={rep} set={set} />
      <Field big label="Professional Notes (PARENT-REPORTED INFORMATION summarized by the professional)" value={rep[`parent_${role}_notes`]} onChange={(v) => set(`parent_${role}_notes`, v)} id={`parent-${role}-notes`} />
    </div>
  );
}

function ResourceRows({ rows = [], lib, onChange }) {
  const upd = (i, k, val) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: val } : r)));
  const add = (r = { category: lib.resource_categories[0], resource: "", focus: "" }) => {
    if (r.resource && rows.some((x) => x.resource === r.resource)) { toast.info(`${r.resource.split(" — ")[0]} is already in the table`); return; }
    onChange([...rows, r]);
  };
  const cat = (p) => (/education/i.test(p.specialty) ? "Educational Assessment" : /children in the middle/i.test(p.specialty) ? "Parent Education" : /options|forensic|facilitat/i.test(p.specialty) ? "Clinical & Forensics" : "Joint / Co-Parenting");
  return (
    <div className="space-y-2" data-testid="lens-resource-rows">
      <div className="hidden sm:grid grid-cols-[1.1fr_1.4fr_2fr_auto] gap-2 rounded-md bg-brand-blue/10 px-2 py-1.5 text-xs font-bold uppercase tracking-widest text-brand-blue"><span>Category</span><span>Recommended Resource / Specialist</span><span>Service Focus &amp; Scope</span><span /></div>
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
  const guides = useWalkthrough(id);
  const { user } = useAuth();
  const [v, setV] = useState(null);
  const [rep, setRep] = useState({});
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(false);
  const [stepMode, setStepMode] = useState(false);
  const [step, setStep] = useState(0);
  const [model, setModel] = useState("gemini");
  const [aiInfo, setAiInfo] = useState(null);
  const aiDraft = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/cases/${id}/professional-report/ai-draft`, { fields: rep, model });
      const empty = Object.keys(data.fields).filter((k) => !(rep[k] || "").trim());
      const keys = empty.length ? empty : Object.keys(data.fields);
      setRep((r) => ({ ...r, ...Object.fromEntries(keys.map((k) => [k, data.fields[k]])), ai_drafts: data.ai_drafts, ...(data.research_base ? { research_base: data.research_base } : {}) }));
      setAiInfo(data);
      toast.success(`${data.model}${data.source === "rule_based" ? " unavailable — rule-based" : ""} draft filled ${keys.length} section${keys.length === 1 ? "" : "s"}. Review and edit before finalizing.`);
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const set = (k, val) => setRep((r) => ({ ...r, [k]: val }));
  const apply = (data) => { setV(data); setRep(data.report); };
  const needsReview = (k) => { const d = rep.ai_drafts?.[k]; return Boolean(d && !d.accepted_at && (rep[k] || "").trim() === (d.text || "").trim()); };
  const acceptDraft = (k) => api.post("/assistant/accept-draft", { case_id: id, field: k }).then((r) => { setRep((x) => ({ ...x, ai_drafts: r.data.ai_drafts })); toast.success("Draft accepted as your text"); }).catch((e) => toast.error(formatApiError(e)));
  const Field = (props) => <FieldBase {...props} badge={needsReview(props.id) ? <DraftBadge id={props.id} onAccept={() => acceptDraft(props.id)} /> : null} />;
  const [assistantOpen, setAssistantOpen] = useState(false);
  const reload = () => api.get(`/cases/${id}/professional-report`).then((r) => apply(r.data)).catch(() => {});
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
      {(v?.readiness || []).find((x) => x.key === "joint")?.done && <Button variant="outline" size="sm" asChild><a href={`${process.env.REACT_APP_BACKEND_URL}/api/cases/${id}/professional-report/bundle.zip`} download title="Joint Report + Professional Report in one ZIP" data-testid="lens-bundle-btn"><Download className="h-4 w-4 mr-1" /> Download Both (ZIP)</a></Button>}
      <Button size="sm" onClick={() => save("final")} disabled={busy || !rep.signature_name} data-testid="lens-finalize-btn"><FileCheck2 className="h-4 w-4 mr-1" /> Finalize Report</Button>
      <select value={rep.status} onChange={(e) => save(e.target.value)} className="h-9 rounded-md border border-input bg-white px-2 text-sm" data-testid="lens-status-select">{lib.statuses.map((s) => <option key={s} value={s}>{STATUS[s]}</option>)}</select>
      {top && <AiPrivacyWarning testId="ai-privacy-warning-lens" />}
      {top && <NeutralityCheck id={id} rep={rep} />}
      {top && rep.status !== "final" && rep.status !== "submitted_to_court" && <span className="flex items-center gap-1 rounded-md border border-brand-purple/30 bg-brand-purple/5 px-2" data-testid="lens-ai-block">
        <select value={model} onChange={(e) => setModel(e.target.value)} className="h-7 rounded-md border border-input bg-white px-1 text-xs" data-testid="lens-ai-model-select">{(lib.ai_models || []).map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}</select>
        <Button variant="ghost" size="sm" onClick={aiDraft} disabled={busy} data-testid="lens-ai-draft-btn"><Sparkles className="h-4 w-4 mr-1" /> AI-assist draft</Button>
      </span>}
    </div>
  );
  const aiNotice = aiInfo && <p className="rounded-md border-l-4 border-amber-500 bg-amber-50 p-2 text-xs" data-testid="lens-ai-notice"><strong>{aiInfo.label}</strong> — generated with {aiInfo.model}{aiInfo.source === "rule_based" ? " (model unavailable; rule-based text used)" : ""}. The professional must review, edit and certify every AI-assisted section before finalizing. AI text makes no legal conclusion or custody recommendation.</p>;
  const S = (n, title, id, body) => ({ id, title, el: <Sec n={n} title={title} id={id} guides={guides}>{body}</Sec> });
  const sections = [
    S(1, "Case & Assessment Overview", "case", <>
              <p className="text-sm leading-relaxed" data-testid="lens-intro">{notes.intro}</p>
              <div className="grid gap-3 sm:grid-cols-3">{[["matter_name", "Case / Matter Name"], ["court_county", "Court / County"], ["cause_number", "Cause Number"], ["professional_role", "Professional Role"], ["parent_a_name", "Parent A Name"], ["parent_b_name", "Parent B Name"]].map(([k, l]) => <Field key={k} label={l} value={rep[k]} onChange={(val) => set(k, val)} id={k} />)}<label className="block text-sm"><span className="font-medium">Case ID</span><input readOnly value={v.case.case_code || ""} className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm" data-testid="lens-case-id" /></label><label className="block text-sm"><span className="font-medium">Professional Name</span><input readOnly value={rep.professional_name || ""} className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm" data-testid="lens-professional-name" /></label><Field label="Report Date" type="date" value={rep.report_date} onChange={(val) => set("report_date", val)} id="report_date" /></div>
              <div><p className="text-sm font-medium">Assessments completed</p><ul className="mt-1 flex flex-wrap gap-3 text-xs" data-testid="lens-assessments">{readiness.map((r) => <li key={r.key} className="flex items-center gap-1">{r.done ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}{r.label}{r.na && !r.done ? " (N/A)" : ""}</li>)}</ul></div>
              <Field big label="Sources of information considered" hint="Assessments, screenings, Joint Report, sessions, documents reviewed — with completion dates." value={rep.sources_considered} onChange={(val) => set("sources_considered", val)} id="sources_considered" />
</>),
    S(2, "Alignment Snapshot & Safety Screening", "snapshot", <>
              <p className="text-xs text-muted-foreground">Where each parent and the co-parenting dynamic sit on the 1–10 scale, and whether a joint process is appropriate.</p>
              <AlignmentStatusGrid rep={rep} />
              <div className="grid gap-3 sm:grid-cols-3"><Rating label="Parent A (1–10)" value={rep.parent_a_rating} onChange={(val) => set("parent_a_rating", val)} id="snapshot-a" /><Rating label="Parent B (1–10)" value={rep.parent_b_rating} onChange={(val) => set("parent_b_rating", val)} id="snapshot-b" /><Rating label="Joint (1–10)" value={rep.joint_rating} onChange={(val) => set("joint_rating", val)} id="snapshot-joint" /></div>
              <div className="rounded-md border border-amber-300 bg-white p-4 space-y-3" data-testid="lens-safety">
                <h3 className="font-semibold text-align-green">Safety screening (IPV &amp; coercive control)</h3>
                <p className="rounded-r-md border-l-4 border-amber-500 bg-amber-50 p-3 text-xs" data-testid="lens-safety-alert">{notes.alert}</p>
                <ImportedScreening screening={v?.safety_screening} rep={rep} caseId={id} pathway={v?.safety_pathway} />
                <div className="grid gap-3 sm:grid-cols-2"><Radio label="Parent A Family Violence Assessment" options={lib.receipt_options} value={rep.fv_a_received} onChange={(val) => set("fv_a_received", val)} id="fv-a" /><Radio label="Parent B Family Violence Assessment" options={lib.receipt_options} value={rep.fv_b_received} onChange={(val) => set("fv_b_received", val)} id="fv-b" /></div>
                <p className="text-xs font-semibold" data-testid="lens-fv-both">{rep.fv_a_received === "Received" && rep.fv_b_received === "Received" ? "✓ Both Assessments Received" : "Both assessments not yet received"}</p>
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
              </div>
</>),
    S(3, `Parent A Perspective${rep.parent_a_name ? ` — ${rep.parent_a_name}` : ""}`, "parent-a", <><p className="text-xs italic text-muted-foreground">Presented separately and neutrally — concerns, priorities, perceptions and identified needs — without determining which account is correct.</p><ParentBlock Field={Field} role="a" rep={rep} cls={cls.parent_a} set={set} /><IndividualScaleTable scale={lib.scale_table} row={cls.parent_a?.row} rating={rep.parent_a_rating} role="a" name={rep.parent_a_name} growth={growthOf(rep, "a")} /></>),
    S(4, `Parent B Perspective${rep.parent_b_name ? ` — ${rep.parent_b_name}` : ""}`, "parent-b", <><ParentBlock Field={Field} role="b" rep={rep} cls={cls.parent_b} set={set} /><IndividualScaleTable scale={lib.scale_table} row={cls.parent_b?.row} rating={rep.parent_b_rating} role="b" name={rep.parent_b_name} growth={growthOf(rep, "b")} /></>),
    S(5, "Joint Co-Parenting Assessment", "joint", <>
              <div className="rounded-md border border-border bg-white p-4 space-y-3" data-testid="lens-joint">
                <Rating label="Joint Co-Parenting Rating (1–10)" value={rep.joint_rating} onChange={(val) => set("joint_rating", val)} id="joint-rating" /><Band cls={cls.joint} joint />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field big label="Areas of alignment" value={rep.alignment_agreements ?? rep.joint_strengths} onChange={(val) => set("alignment_agreements", val)} id="alignment_agreements" />
                  <Field big label="Areas of partial alignment" value={rep.partial_alignment} onChange={(val) => set("partial_alignment", val)} id="partial_alignment" />
                  <Field big label="Areas of differing perspectives" value={rep.alignment_disagreements ?? rep.joint_gaps} onChange={(val) => set("alignment_disagreements", val)} id="alignment_disagreements" />
                  <Field big label="Shared concerns" value={rep.shared_concerns} onChange={(val) => set("shared_concerns", val)} id="shared_concerns" />
                </div>
                <Field big label="Issues requiring further discussion or professional attention" value={rep.joint_notes} onChange={(val) => set("joint_notes", val)} id="joint_notes" />
              </div>
              <JointScaleTable scale={lib.scale_table} row={cls.joint?.row} rating={rep.joint_rating} />
</>),
    S(6, "Child-Focused Legal Issues", "child", <>              <p className="text-xs text-muted-foreground">Tick each area affecting the child's needs and circumstances; categories suggested by the Joint Report are pre-ticked for your review.</p>
              <ChildFocusList categories={lib.child_focus_categories} value={rep.child_focus || {}} onChange={(val) => set("child_focus", val)} />
              <ChildFocusSuggest id={id} value={rep.child_focus || {}} onChange={(val) => set("child_focus", val)} />
</>),
    S(7, "Options & Resources", "resources", <><ResourceRows rows={rep.resource_rows} lib={lib} onChange={(rows) => set("resource_rows", rows)} /><ResearchBase id={id} value={rep.research_base} onChange={(rb) => set("research_base", rb)} /><ResearchPanel isAdmin={user?.role === "admin"} onAddRow={(row) => set("resource_rows", [...(rep.resource_rows || []), row])} /></>),
    S(8, "Conflict Resolution Pathways", "conflict", <>              <p className="text-xs text-muted-foreground">{notes.purpose}</p>
              <PathwayPicker lib={{ ...lib, notes }} rep={rep} cls={cls} set={set} />
              <Field big label="Why these pathways are relevant to the issues identified" hint="Explain the fit to the type of conflict — not just a list of services. Required to finalize." value={rep.pathway_rationale ?? rep.conflict_management_rationale} onChange={(val) => set("pathway_rationale", val)} id="pathway_rationale" />
              <p className="text-xs italic" data-testid="lens-rating-note">{notes.rating}</p>
</>),
    S(9, "Legal Conflict & Agreement-Building Analysis", "legal", <>
              <p className="text-xs text-muted-foreground">Where agreement is realistic and what still needs resolution. Procedural and neutral — no prediction of court outcomes.</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field big label="Areas potentially capable of agreement" hint="One per line." value={rep.agreement_building_opportunities} onChange={(val) => set("agreement_building_opportunities", val)} id="agreement_building_opportunities" />
                <Field big label="Issues requiring further resolution" hint="One per line." value={rep.issues_requiring_attention} onChange={(val) => set("issues_requiring_attention", val)} id="issues_requiring_attention" />
                <Field big label="Existing agreements / orders noted" value={rep.existing_agreements} onChange={(val) => set("existing_agreements", val)} id="existing_agreements" />
                <Field big label="Procedural considerations" value={rep.procedural_considerations} onChange={(val) => set("procedural_considerations", val)} id="procedural_considerations" />
              </div></>),
    S(10, "Professional Legal Statement & Roadmap", "summary", <>
              <p className="text-xs italic text-muted-foreground">Your own observations, interpretation, recommendations and conclusions — clearly distinct from parent-reported information, individual responses, joint comparisons and any system- or AI-generated summary. You remain responsible for the judgment in this section.</p>
              <Field big label="Professional statement" value={rep.professional_summary} onChange={(val) => set("professional_summary", val)} id="professional_summary" />
              <ParallelSummaryHelper id={id} onInsert={(t) => set("professional_summary", `${(rep.professional_summary || "").trim()}${rep.professional_summary?.trim() ? "\n\n" : ""}${t}`)} />
              <Field big label="Short-Term Goals / 90-Day Action Plan (Next 30 to 90 Days)" hint="One goal per line, as “Title: concrete action”." value={rep.short_term_goals} onChange={(val) => set("short_term_goals", val)} id="short_term_goals" />
              <Field big label="How We Will Know Things Are Improving (Success Indicators)" hint="One observable indicator per line, e.g. “Fewer transition disputes.”" value={rep.success_indicators} onChange={(val) => set("success_indicators", val)} id="success_indicators" />
              <Field big label="Long-Term Goals (6 to 12 Months)" hint="One goal per line." value={rep.long_term_goals} onChange={(val) => set("long_term_goals", val)} id="long_term_goals" />
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm"><span className="font-medium">Reassessment interval</span><select value={rep.reassess_interval || ""} onChange={(e) => set("reassess_interval", e.target.value)} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid="lens-reassess_interval">{lib.reassess_intervals.map((o) => <option key={o}>{o}</option>)}</select></label>
                <Field label="Next Review / Reassessment Date" type="date" value={rep.next_review_date} onChange={(val) => set("next_review_date", val)} id="next_review_date" />
              </div>
              <div className="grid gap-3 sm:grid-cols-2"><Field big label="When Score Moves Up" value={rep.reassess_up} onChange={(val) => set("reassess_up", val)} id="reassess_up" /><Field big label="When Score Drops" value={rep.reassess_down} onChange={(val) => set("reassess_down", val)} id="reassess_down" /></div>
              <ReportPrinciple notes={notes} />
</>),
    S(11, "Concise Court Summary", "court-summary", <>              <p className="text-xs text-muted-foreground">1–3 paragraphs for the court, referring professional, mediator or other authorized recipient. Included in the frozen court submission.</p>
              <Field big label="Professional summary" value={rep.court_summary_text} onChange={(val) => set("court_summary_text", val)} id="court_summary_text" />
              <h3 className="font-semibold text-align-green">Professional Certification</h3>
              <p className="text-xs italic">This report reflects the professional's review of the individual assessments, safety screenings and Joint Report. It contains no custody recommendation, credibility determination, diagnosis or legal conclusion.</p>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Professional Signature Name" value={rep.signature_name} onChange={(val) => set("signature_name", val)} id="signature_name" /><Field label="Professional Title" value={rep.professional_title} onChange={(val) => set("professional_title", val)} id="professional_title" /></div>
              {rep.finalized_at && <p className="text-xs text-align-green font-semibold" data-testid="lens-finalized">Date finalized: {rep.finalized_at.slice(0, 10)}</p>}
              <ReportDisclaimer notes={notes} signature={rep.signature_name} date={rep.finalized_at?.slice(0, 10)} />
</>),
  ];
  return (
    <div className="min-h-screen bg-white" data-testid="lens-page">
      <header className="border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2"><Link to={`/joint/${id}`} className="flex items-center gap-1.5 text-sm text-muted-foreground" data-testid="lens-back"><ArrowLeft className="h-4 w-4" /> Back to Case</Link><BrandLogo size="text-xl" /><span className="rounded-full bg-brand-purple/10 px-3 py-1 text-xs font-semibold text-brand-purple" data-testid="lens-status">{STATUS[rep.status]}</span></div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5">
        <ReportHeader />
        <AlignAssistant userId={user?.id || "anon"} caseId={id} caseLabel={v?.case?.case_code} open={assistantOpen} onOpenChange={setAssistantOpen} onInserted={reload} />
        <ReportCover pro={{ ...(v?.professional || {}), name: rep.cover_name || v?.professional?.name, email: rep.cover_email || v?.professional?.email, phone: rep.cover_phone || v?.professional?.phone, address: rep.cover_address || v?.professional?.address, title: rep.cover_title || v?.professional?.title, bar_number: rep.cover_bar_number || v?.professional?.bar_number, license_number: rep.cover_license_number || v?.professional?.license_number, submission_date: rep.submission_date }} origin={v?.content_origin} testId="lens-cover" imageBase={`${process.env.REACT_APP_BACKEND_URL}/api/me/profile/image`}>
          <details className="mt-3 rounded-md border border-dashed border-border p-3" data-testid="lens-cover-profile">
            <summary className="cursor-pointer text-xs font-semibold text-brand-purple">My profile details (fills every report cover automatically)</summary>
            <div className="mt-3"><ProfileContactForm onSaved={reload} /></div>
          </details>
          <details className="mt-3 rounded-md border border-dashed border-border p-3" data-testid="lens-cover-signature-capture">
            <summary className="cursor-pointer text-xs font-semibold text-brand-purple">Signature (draw or upload)</summary>
            <div className="mt-3"><SignatureCapture hasSignature={!!v?.professional?.images?.signature} onChanged={reload} /></div>
          </details>
          <details className="mt-3 rounded-md border border-dashed border-border p-3" data-testid="lens-cover-override">
            <summary className="cursor-pointer text-xs font-semibold text-brand-purple">Cover details for this report (profile values are used when blank)</summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">{[["cover_name", "Professional Name"], ["cover_title", "Title"], ["cover_bar_number", "Bar Number"], ["cover_license_number", "License Number"], ["cover_email", "Email"], ["cover_phone", "Phone"], ["submission_date", "Date of submission"], ["cover_address", "Office / Mailing Address"]].map(([k, l]) => <Field key={k} label={l} value={rep[k]} onChange={(val) => set(k, val)} id={k} big={k === "cover_address"} />)}</div>
          </details>
        </ReportCover>
        <p className="rounded-md border-l-4 border-brand-purple bg-brand-purple/5 p-3 text-sm" data-testid="lens-principle-notice"><strong className="text-brand-purple">Report Principle:</strong> Parent statements, system-generated comparisons, AI-assisted summaries, and professional observations are identified separately so the source of each statement remains clear.</p>
        <SixQuestions anchor={(n) => GUIDE_SEC[n]} testId="lens-six-questions" />
        <SourceLegend testId="lens-source-legend" />
        <WorkflowGuide kind="legal_lens" />
        <WalkthroughOverview guides={guides} anchor={(n) => GUIDE_SEC[n]} done={(n) => (GUIDE_FIELDS[n] || []).some((k) => { const v = rep?.[k]; return Array.isArray(v) ? v.length > 0 : v && typeof v === "object" ? Object.values(v).some((x) => x?.checked) : Boolean(v); })} />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <ol className="flex flex-wrap gap-1 text-[11px]" data-testid="lens-steps">{STEPS.map((s, i) => <li key={s} className={`rounded-full border px-2 py-0.5 ${stepMode && i === step ? "bg-brand-purple text-white border-brand-purple" : "border-brand-purple/30 text-brand-purple"}`}>{i + 1}. {s}</li>)}</ol>
          <Button variant={stepMode ? "default" : "outline"} size="sm" onClick={() => { setStepMode((v) => !v); setStep(0); }} className={stepMode ? "bg-brand-purple text-white" : ""} data-testid="lens-step-mode-toggle">{stepMode ? "Exit guided mode" : "Guided step mode"}</Button>
        </div>
        {actions(true)}
        {aiNotice}
        <AiDraftComparison drafts={rep.ai_drafts} rep={rep} />
        {preview ? <iframe title="Report preview" src={pdf} className="h-[80vh] w-full rounded-lg border border-border" data-testid="lens-preview-frame" /> : (
          <>
{sections.map((sec, i) => (!stepMode || i === step) && <div key={sec.id} className="space-y-5">{sec.id === "legal" && <StatementDivider />}{sec.el}</div>)}
            {stepMode && (
              <div className="sticky bottom-3 z-10 flex items-center justify-between gap-3 rounded-xl border border-brand-purple/30 bg-white/95 p-3 shadow-lg backdrop-blur" data-testid="lens-step-nav">
                <Button variant="outline" size="sm" onClick={() => setStep((x) => Math.max(0, x - 1))} disabled={step === 0} data-testid="lens-step-back">← Back</Button>
                <div className="flex-1"><div className="h-2 w-full overflow-hidden rounded-full bg-secondary"><div className="h-full bg-brand-purple transition-[width]" style={{ width: `${((step + 1) / sections.length) * 100}%` }} data-testid="lens-step-progress" /></div><p className="mt-1 text-center text-xs text-muted-foreground">Section {step + 1} of {sections.length} · {sections[step].title}</p></div>
                {step < sections.length - 1 ? <Button size="sm" className="bg-brand-purple hover:bg-brand-purple/90 text-white" onClick={() => { save(); setStep((x) => x + 1); }} data-testid="lens-step-next">Save & Next →</Button> : <Button size="sm" className="bg-align-green hover:bg-align-green/90 text-white" onClick={() => { save(); setStepMode(false); }} data-testid="lens-step-finish">Save & review all</Button>}
              </div>
            )}
            {actions(false)}
          </>
        )}
        <p className="text-center text-xs text-brand-purple font-semibold">{notes.tagline}</p>
      </main>
    </div>
  );
}
