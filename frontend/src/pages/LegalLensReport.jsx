import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, Circle, Download, Eye, FileCheck2, Save } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const STEPS = ["Case Information", "Safety First", "Parent A Individual Assessment", "Parent A Resources", "Parent B Individual Assessment", "Parent B Resources", "Joint Co-Parenting Assessment", "Joint Resources", "Parent Alignment", "Conflict Management", "Roadmap", "Professional Summary", "Generate PDF"];
const STATUS = { draft: "Draft", under_review: "Under Review", final: "Final", submitted_to_court: "Submitted to Court" };
const Sec = ({ n, title, children, id }) => <section className="rounded-lg border border-border bg-[#f7f3fb] p-6" data-testid={`lens-${id}`}><h2 className="text-lg font-semibold text-brand-purple flex items-center gap-2"><span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{n}</span>{title}</h2><div className="mt-4 space-y-3 text-sm">{children}</div></section>;
const Field = ({ label, value, onChange, id, type = "text", big }) => <label className="block text-sm"><span className="font-medium">{label}</span>{big ? <Textarea value={value || ""} onChange={(e) => onChange(e.target.value)} className="mt-1 min-h-[110px] bg-white" data-testid={`lens-${id}`} /> : <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} className="mt-1 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid={`lens-${id}`} />}</label>;
const Radio = ({ label, options, value, onChange, id }) => <div><p className="text-sm font-medium">{label}</p><div className="mt-1 flex flex-wrap gap-3">{options.map((o) => <label key={o} className="flex items-center gap-1.5 text-sm"><input type="radio" checked={value === o} onChange={() => onChange(o)} data-testid={`lens-${id}-${o.split(/[ ,/]/)[0].toLowerCase()}`} />{o}</label>)}</div></div>;
const Checks = ({ options, value = [], onChange, id }) => <ul className="grid gap-1 sm:grid-cols-2">{options.map((o) => <li key={o}><label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={value.includes(o)} onChange={() => onChange(value.includes(o) ? value.filter((x) => x !== o) : [...value, o])} data-testid={`lens-${id}`} /><span>{o}</span></label></li>)}</ul>;
const Provider = ({ value = {}, onChange, id }) => <div className="grid gap-2 sm:grid-cols-3 rounded-md border border-border bg-white p-3" data-testid={`lens-${id}`}>{[["name", "Name"], ["specialty", "Specialty"], ["contact", "Contact Information"]].map(([k, l]) => <label key={k} className="text-xs font-medium">{l}<input value={value[k] || ""} onChange={(e) => onChange({ ...value, [k]: e.target.value })} className="mt-1 h-8 w-full rounded-md border border-input px-2 text-sm font-normal" data-testid={`lens-${id}-${k}`} /></label>)}</div>;
const Band = ({ cls, joint }) => cls ? <div className="rounded-md border border-brand-purple/30 bg-white p-3 text-sm" data-testid="lens-band"><p className="font-semibold text-brand-purple">{cls.range}: {cls.label}{joint && <span className="ml-2 rounded-full bg-brand-purple/10 px-2 py-0.5 text-xs">Mode: {cls.mode}</span>}</p><div className="mt-2 grid gap-3 sm:grid-cols-2"><div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{joint ? "Strengths may include" : "Where this level may do well"}</p><ul className="list-disc pl-4">{cls.strengths.map((s) => <li key={s}>{s}</li>)}</ul></div><div><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Possible gaps</p><ul className="list-disc pl-4">{cls.gaps.map((s) => <li key={s}>{s}</li>)}</ul></div></div></div> : <p className="text-xs italic text-muted-foreground">Enter a 1–10 rating to see the automatic classification.</p>;
const Rating = ({ label, value, onChange, id }) => <label className="flex items-center gap-3 text-sm"><span className="font-medium">{label}</span><input type="range" min="1" max="10" value={value || 5} onChange={(e) => onChange(Number(e.target.value))} className="flex-1 accent-brand-purple" data-testid={`lens-${id}`} /><span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-purple text-sm font-bold text-white" data-testid={`lens-${id}-value`}>{value || "–"}</span></label>;

function ParentBlock({ role, n, rep, cls, lib, set }) {
  const name = rep[`parent_${role}_name`] || `Parent ${role.toUpperCase()}`;
  const res = rep[`parent_${role}_resources`] || [];
  return (
    <>
      <Sec n={n} title={`Individual Assessment — ${name}`} id={`parent-${role}`}>
        <Rating label="Rating (1–10)" value={rep[`parent_${role}_rating`]} onChange={(v) => set(`parent_${role}_rating`, v)} id={`parent-${role}-rating`} />
        <Band cls={cls} />
        <Field big label={`Where ${name} Does Well`} value={rep[`parent_${role}_strengths`]} onChange={(v) => set(`parent_${role}_strengths`, v)} id={`parent-${role}-strengths`} />
        <Field big label={`Where ${name} Struggles`} value={rep[`parent_${role}_gaps`]} onChange={(v) => set(`parent_${role}_gaps`, v)} id={`parent-${role}-gaps`} />
        <Field big label="Professional Notes" value={rep[`parent_${role}_notes`]} onChange={(v) => set(`parent_${role}_notes`, v)} id={`parent-${role}-notes`} />
      </Sec>
      <Sec n={`${n}b`} title={`${name} Individual Resources`} id={`parent-${role}-resources`}>
        <Checks options={lib.individual_resources} value={res} onChange={(v) => set(`parent_${role}_resources`, v)} id={`parent-${role}-resource`} />
        {res.includes("Additional Counselor / Provider") && <Provider value={rep[`parent_${role}_provider`]} onChange={(v) => set(`parent_${role}_provider`, v)} id={`parent-${role}-provider`} />}
      </Sec>
    </>
  );
}

export default function LegalLensReport() {
  const { id } = useParams();
  const [v, setV] = useState(null);
  const [rep, setRep] = useState({});
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(false);
  const set = (k, val) => setRep((r) => ({ ...r, [k]: val }));
  const apply = (data) => { setV(data); setRep(data.report); };
  useEffect(() => { api.get(`/cases/${id}/professional-report`).then((r) => apply(r.data)).catch((e) => toast.error(formatApiError(e))); }, [id]);
  useEffect(() => { if (!v) return; const t = setTimeout(() => api.put(`/cases/${id}/professional-report`, { fields: { parent_a_rating: rep.parent_a_rating, parent_b_rating: rep.parent_b_rating, joint_rating: rep.joint_rating } }).then((r) => setV((x) => ({ ...x, classification: r.data.classification }))).catch(() => {}), 400); return () => clearTimeout(t); }, [rep.parent_a_rating, rep.parent_b_rating, rep.joint_rating]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async (status) => { setBusy(true); try { const { data } = await api.put(`/cases/${id}/professional-report`, { fields: rep, ...(status ? { status } : {}) }); apply(data); toast.success(status ? `Report marked ${STATUS[status]}` : "Draft saved"); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); } };
  if (!v) return <div className="min-h-screen bg-white" data-testid="lens-loading" />;
  const { classification: cls, library: lib, notes, readiness } = v;
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/cases/${id}/professional-report/pdf`;
  const actions = (
    <div className="flex flex-wrap gap-2" data-testid="lens-actions">
      <Button variant="outline" size="sm" onClick={() => save()} disabled={busy} data-testid="lens-save-btn"><Save className="h-4 w-4 mr-1" /> Save Draft</Button>
      <Button variant="outline" size="sm" onClick={async () => { await save(); setPreview(!preview); }} disabled={busy} data-testid="lens-preview-btn"><Eye className="h-4 w-4 mr-1" /> {preview ? "Back to Editor" : "Preview Report"}</Button>
      <Button variant="outline" size="sm" asChild data-testid="lens-pdf-btn"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> Generate PDF</a></Button>
      <Button size="sm" onClick={() => save("final")} disabled={busy || !rep.signature_name} data-testid="lens-finalize-btn"><FileCheck2 className="h-4 w-4 mr-1" /> Finalize Report</Button>
      <select value={rep.status} onChange={(e) => save(e.target.value)} className="h-9 rounded-md border border-input bg-white px-2 text-sm" data-testid="lens-status-select">{lib.statuses.map((s) => <option key={s} value={s}>{STATUS[s]}</option>)}</select>
    </div>
  );
  return (
    <div className="min-h-screen bg-white" data-testid="lens-page">
      <header className="border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2"><Link to={`/joint/${id}`} className="flex items-center gap-1.5 text-sm text-muted-foreground" data-testid="lens-back"><ArrowLeft className="h-4 w-4" /> Back to Case</Link><BrandLogo size="text-xl" /><span className="rounded-full bg-brand-purple/10 px-3 py-1 text-xs font-semibold text-brand-purple" data-testid="lens-status">{STATUS[rep.status]}</span></div></header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-brand-purple" data-testid="lens-title">SA CoParents Legal Lens Review and Report to Court</h1>
        <ol className="flex flex-wrap gap-1 text-[11px]" data-testid="lens-steps">{STEPS.map((s, i) => <li key={s} className="rounded-full border border-brand-purple/30 px-2 py-0.5 text-brand-purple">{i + 1}. {s}</li>)}</ol>
        <ul className="flex flex-wrap gap-3 text-xs" data-testid="lens-readiness">{readiness.map((r) => <li key={r.key} className="flex items-center gap-1">{r.done ? <CheckCircle2 className="h-4 w-4 text-align-green" /> : <Circle className="h-4 w-4 text-muted-foreground" />}{r.label}{r.na && !r.done ? " (N/A)" : ""}</li>)}</ul>
        {actions}
        {preview ? <iframe title="Report preview" src={pdf} className="h-[80vh] w-full rounded-lg border border-border" data-testid="lens-preview-frame" /> : (
          <>
            <Sec n={1} title="Case Information" id="case"><div className="grid gap-3 sm:grid-cols-3">{[["matter_name", "Case / Matter Name"], ["court_county", "Court / County"], ["cause_number", "Cause Number"], ["professional_role", "Professional Role"], ["parent_a_name", "Parent A Name"], ["parent_b_name", "Parent B Name"]].map(([k, l]) => <Field key={k} label={l} value={rep[k]} onChange={(val) => set(k, val)} id={k} />)}<label className="block text-sm"><span className="font-medium">Case ID</span><input readOnly value={v.case.case_code || ""} className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm" data-testid="lens-case-id" /></label><label className="block text-sm"><span className="font-medium">Professional Name</span><input readOnly value={rep.professional_name || ""} className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm" data-testid="lens-professional-name" /></label><Field label="Report Date" type="date" value={rep.report_date} onChange={(val) => set("report_date", val)} id="report_date" /></div></Sec>
            <Sec n={2} title="Safety First — Receipt of Individual Family Violence Assessment(s)" id="safety">
              <Radio label="Parent A Family Violence Assessment" options={lib.receipt_options} value={rep.fv_a_received} onChange={(val) => set("fv_a_received", val)} id="fv-a" />
              <Radio label="Parent B Family Violence Assessment" options={lib.receipt_options} value={rep.fv_b_received} onChange={(val) => set("fv_b_received", val)} id="fv-b" />
              <p className="text-xs font-semibold" data-testid="lens-fv-both">{rep.fv_a_received === "Received" && rep.fv_b_received === "Received" ? "✓ Both Assessments Received" : "Both assessments not yet received"}</p>
              <Radio label="Joint Process Appropriate?" options={lib.joint_process_options} value={rep.joint_process_appropriate} onChange={(val) => set("joint_process_appropriate", val)} id="joint-process" />
              <Field big label="Safety Notes / Safeguards" value={rep.safety_notes} onChange={(val) => set("safety_notes", val)} id="safety_notes" />
              <p className="rounded-md border-l-4 border-red-600 bg-red-50 p-2 text-xs" data-testid="lens-safety-note">{notes.safety}</p>
            </Sec>
            <ParentBlock role="a" n={3} rep={rep} cls={cls.parent_a} lib={lib} set={set} />
            <ParentBlock role="b" n={4} rep={rep} cls={cls.parent_b} lib={lib} set={set} />
            <Sec n={5} title="Joint Co-Parenting Assessment" id="joint">
              <Rating label="Joint Co-Parenting Rating (1–10)" value={rep.joint_rating} onChange={(val) => set("joint_rating", val)} id="joint-rating" /><Band cls={cls.joint} joint />
              <Field big label="Where the Parents Do Well Together" value={rep.joint_strengths} onChange={(val) => set("joint_strengths", val)} id="joint_strengths" />
              <Field big label="Where the Parents Struggle Together" value={rep.joint_gaps} onChange={(val) => set("joint_gaps", val)} id="joint_gaps" />
              <Field big label="Professional Joint Assessment Notes" value={rep.joint_notes} onChange={(val) => set("joint_notes", val)} id="joint_notes" />
            </Sec>
            <Sec n={6} title="Joint Resources" id="joint-resources"><Checks options={lib.joint_resources} value={rep.joint_resources} onChange={(val) => set("joint_resources", val)} id="joint-resource" />{(rep.joint_resources || []).includes("Additional Expert / Provider") && <Provider value={rep.joint_provider} onChange={(val) => set("joint_provider", val)} id="joint-provider" />}</Sec>
            <Sec n={7} title="Parent Alignment — Based on Joint Report" id="alignment">
              <Field big label="Where the Parents Agree / Are Aligned (e.g., child's school, medical treatment, extracurricular activities, parenting schedule, communication expectations, child-focused goals, shared priorities)" value={rep.alignment_agreements} onChange={(val) => set("alignment_agreements", val)} id="alignment_agreements" />
              <Field big label="Where the Parents Do Not Agree / Are Not Aligned (e.g., schedule changes, communication, transportation, medical decisions, school decisions, parenting-plan issues, household expectations)" value={rep.alignment_disagreements} onChange={(val) => set("alignment_disagreements", val)} id="alignment_disagreements" />
              <Field big label="Partial Alignment / Potential Areas for Agreement (common ground that may need clarification, professional guidance, mediation or structured discussion)" value={rep.partial_alignment} onChange={(val) => set("partial_alignment", val)} id="partial_alignment" />
              <Field big label="Professional Alignment Summary — Summarize the significant areas of agreement and disagreement, how they relate to the child's needs, and which issues may require additional resolution." value={rep.alignment_summary} onChange={(val) => set("alignment_summary", val)} id="alignment_summary" />
            </Sec>
            <Sec n={8} title="Conflict Management — Approaches to Conflict" id="conflict">
              <Checks options={lib.conflict_options} value={rep.conflict_management_options} onChange={(val) => set("conflict_management_options", val)} id="conflict-option" />
              {cls.joint && <div className="rounded-md border border-border bg-white p-3" data-testid="lens-guidance"><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Automatic guidance for joint rating {rep.joint_rating} — consider</p><ul className="list-disc pl-4 text-sm">{cls.joint.guidance.map((g) => <li key={g}>{g}</li>)}</ul></div>}
              <Field big label="Conflict Management Rationale / Recommended Structure" value={rep.conflict_management_rationale} onChange={(val) => set("conflict_management_rationale", val)} id="conflict_management_rationale" />
              <p className="text-xs italic" data-testid="lens-rating-note">{notes.rating}</p>
            </Sec>
            <Sec n={9} title="Roadmap" id="roadmap"><Field big label="Short-Term Goals — Next 30 to 90 Days" value={rep.short_term_goals} onChange={(val) => set("short_term_goals", val)} id="short_term_goals" /><Field big label="Long-Term Goals — 6 to 12 Months" value={rep.long_term_goals} onChange={(val) => set("long_term_goals", val)} id="long_term_goals" /></Sec>
            <Sec n={10} title="Professional Summary" id="summary">
              <Field big label="Professional Legal Lens Review and Report to Court — Summarize the individual assessments, joint assessment, areas of alignment and non-alignment, selected resources, conflict-management options, and recommended next steps." value={rep.professional_summary} onChange={(val) => set("professional_summary", val)} id="professional_summary" />
              <div className="grid gap-3 sm:grid-cols-3"><Field label="Next Review / Reassessment Date" type="date" value={rep.next_review_date} onChange={(val) => set("next_review_date", val)} id="next_review_date" /><Field label="Professional Signature Name" value={rep.signature_name} onChange={(val) => set("signature_name", val)} id="signature_name" /><Field label="Professional Title" value={rep.professional_title} onChange={(val) => set("professional_title", val)} id="professional_title" /></div>
              {rep.finalized_at && <p className="text-xs text-align-green font-semibold" data-testid="lens-finalized">Date finalized: {rep.finalized_at.slice(0, 10)}</p>}
            </Sec>
            {actions}
          </>
        )}
        <p className="text-center text-xs text-brand-purple font-semibold">{notes.tagline}</p>
      </main>
    </div>
  );
}
