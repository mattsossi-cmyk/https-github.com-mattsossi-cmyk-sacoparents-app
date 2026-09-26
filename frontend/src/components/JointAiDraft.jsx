import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Sparkles, CheckCircle2, Trash2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { EvaluationEditor } from "@/components/EvaluationEditor";

const LIST_FIELDS = [["alignment_statements", "What both parents agree about"], ["child_needs", "Child's identified needs"], ["conversation", "Conversation starters"], ["questions", "Reflection questions"], ["next_steps", "Next steps"]];
const EVAL_KEYS = ["safety_status", "parent_a_profile", "parent_b_profile", "scale", "short_term_goals", "long_term_goals", "resources"];

const toText = (v) => (Array.isArray(v) ? v.join("\n") : v || "");
const fromText = (k, t) => (k === "alignment_paragraph" ? t.trim() : t.split("\n").map((s) => s.trim()).filter(Boolean));

export const JointAiDraft = ({ reportId, onChanged }) => {
  const [d, setD] = useState(null);
  const [edit, setEdit] = useState({});
  const [evalEdit, setEvalEdit] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get(`/joint/reports/${reportId}/ai-joint-draft`).then((r) => { setD(r.data); setEdit({}); setEvalEdit(null); }).catch(() => {});
  useEffect(() => { load(); }, [reportId]); // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (fn, ok) => {
    setBusy(true);
    try { await fn(); toast.success(ok); await load(); onChanged?.(); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const dirty = Object.keys(edit).length > 0 || evalEdit !== null;
  const editedFields = () => ({ ...Object.fromEntries(Object.entries(edit).map(([k, t]) => [k, fromText(k, t)])), ...(evalEdit ? Object.fromEntries(EVAL_KEYS.filter((k) => k in evalEdit).map((k) => [k, evalEdit[k]])) : {}) });
  const generate = () => run(() => api.post(`/joint/reports/${reportId}/ai-joint-draft`), "Gemini draft ready for your review");
  const saveEdits = () => run(() => api.put(`/joint/reports/${reportId}/ai-joint-draft`, { fields: editedFields() }), "Draft edits saved");
  const approve = async () => { if (dirty) await saveEdits(); await run(() => api.post(`/joint/reports/${reportId}/ai-joint-draft/approve`), "Approved — parents and court now see the reviewed AI-assisted report"); };
  const discard = () => run(() => api.post(`/joint/reports/${reportId}/ai-joint-draft/discard`), "AI draft discarded — rule-based report in effect");

  if (!d) return null;
  const has = d.status === "draft" || d.status === "approved";
  const fields = { ...d.fields, ...Object.fromEntries(Object.entries(edit).map(([k, t]) => [k, fromText(k, t)])) };

  return (
    <section className="no-print mb-8 rounded-xl border-2 border-brand-purple/30 bg-white p-5" data-testid="joint-ai-draft">
      <div className="flex flex-wrap items-center gap-3">
        <Sparkles className="h-5 w-5 text-brand-purple shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-sm">Gemini-drafted Joint Report <span className="ml-1 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide" data-testid="joint-ai-status">{d.status === "none" ? "Not drafted" : d.status === "approved" ? "Approved · in effect" : "Draft · review required"}</span></p>
          <p className="text-xs text-muted-foreground">{d.model} rewrites the narrative sections from both parents' answers. Nothing changes for parents or the court until you approve it here. The rule-based report is always the fallback.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={generate} disabled={busy} className="bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="joint-ai-generate-btn">{busy ? "Working…" : has ? "Re-draft" : "Draft with Gemini"}</Button>
          {has && d.status !== "approved" && <Button size="sm" onClick={approve} disabled={busy} className="bg-align-green hover:bg-align-green/90 text-white" data-testid="joint-ai-approve-btn"><CheckCircle2 className="h-4 w-4" /> Approve & publish</Button>}
          {has && dirty && <Button size="sm" variant="outline" onClick={saveEdits} disabled={busy} data-testid="joint-ai-save-btn">Save edits</Button>}
          {has && <Button size="sm" variant="outline" onClick={discard} disabled={busy} data-testid="joint-ai-discard-btn"><Trash2 className="h-4 w-4" /> Discard</Button>}
        </div>
      </div>
      {has && (
        <div className="mt-4 space-y-4" data-testid="joint-ai-fields">
          <p className="text-xs font-bold uppercase tracking-wider text-brand-purple">{d.label}</p>
          <label className="block text-sm"><span className="font-medium">Alignment summary</span>
            <Textarea value={edit.alignment_paragraph ?? toText(fields.alignment_paragraph)} onChange={(e) => setEdit({ ...edit, alignment_paragraph: e.target.value })} className="mt-1 min-h-[70px]" data-testid="joint-ai-field-alignment_paragraph" /></label>
          {LIST_FIELDS.map(([k, label]) => (
            <label key={k} className="block text-sm"><span className="font-medium">{label}</span> <span className="text-xs text-muted-foreground">(one per line)</span>
              <Textarea value={edit[k] ?? toText(fields[k])} onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} className="mt-1 min-h-[80px]" data-testid={`joint-ai-field-${k}`} /></label>
          ))}
          <div>
            <p className="text-sm font-medium">Where the parents see things differently</p>
            {(fields.differences || []).length === 0 ? <p className="text-xs text-muted-foreground italic">No differences drafted.</p> : (fields.differences || []).map((x, i) => (
              <div key={i} className="mt-2 rounded-md border border-border p-3 text-sm" data-testid={`joint-ai-difference-${i}`}>
                <p className="font-semibold">{x.area}</p>
                <p className="mt-1"><span className="text-xs uppercase text-muted-foreground">Parent A:</span> {x.parent_a}</p>
                <p><span className="text-xs uppercase text-muted-foreground">Parent B:</span> {x.parent_b}</p>
                <p className="mt-1 italic text-muted-foreground">{x.reframe}</p>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-brand-purple/20 bg-brand-purple/5 p-4">
            <EvaluationEditor fields={{ ...Object.fromEntries(EVAL_KEYS.map((k) => [k, d.fields[k]])), ...(evalEdit || {}) }} matrix={d.scale_matrix} onChange={setEvalEdit} />
          </div>
        </div>
      )}
    </section>
  );
};
