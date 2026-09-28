import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ChevronRight } from "lucide-react";
import api from "@/lib/api";

const LINKS = { individual: (id) => `/joint/${id}`, joint: (id) => `/joint/${id}`, resources: (id) => `/cases/${id}/professional-report#resources`, pathway: (id) => `/cases/${id}/professional-report#pathway`, report: (id) => `/cases/${id}/professional-report` };
const STATE = { done: "border-align-green bg-align-green text-white", active: "border-brand-purple bg-white text-brand-purple ring-4 ring-brand-purple/15", todo: "border-border bg-white text-muted-foreground" };

export const PipelineStepper = ({ cases, selectedId, onSelect, onBrief, onTrigger }) => {
  const [brief, setBrief] = useState(null);
  useEffect(() => {
    if (!selectedId) { setBrief(null); return; }
    api.get(`/assistant/case-brief/${selectedId}`).then((r) => { setBrief(r.data); onBrief?.(r.data); }).catch(() => setBrief(null));
  }, [selectedId]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!cases.length) return null;
  return (
    <section className="rounded-2xl border border-border bg-white p-5 sm:p-6" data-testid="pipeline-stepper">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div><p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Workflow Pipeline</p><p className="text-sm text-muted-foreground">Progress for the selected case — click a step to jump in.</p></div>
        <select value={selectedId || ""} onChange={(e) => onSelect(e.target.value)} className="h-10 rounded-md border border-input bg-white px-3 text-sm font-semibold" data-testid="pipeline-case-select">
          {cases.map((j) => <option key={j.id} value={j.id}>{j.case_code || j.id.slice(0, 8)} · {j.subject_label}{j.child_name ? ` · ${j.child_name}` : ""}</option>)}
        </select>
      </div>
      <ol className="mt-6 grid gap-3 md:grid-cols-5" data-testid="pipeline-steps">
        {(brief?.steps || []).map((s, i) => (
          <li key={s.key} className="relative flex md:flex-col md:items-start gap-3" data-testid={`pipeline-step-${s.key}`} data-state={s.state}>
            <Link to={LINKS[s.key](selectedId)} onClick={() => s.key === "pathway" && onTrigger?.("pathway", "click")} className="flex items-center gap-3 md:flex-col md:items-start group">
              <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold transition-colors ${STATE[s.state]}`}>{s.state === "done" ? <Check className="h-4 w-4" /> : i + 1}</span>
              <span><span className="block text-sm font-semibold group-hover:underline">{s.label}</span><span className="block text-xs text-muted-foreground" data-testid={`pipeline-step-${s.key}-detail`}>{s.detail}</span></span>
            </Link>
            {i < 4 && <ChevronRight className="hidden md:block absolute -right-3 top-2 h-5 w-5 text-muted-foreground/50" />}
          </li>
        ))}
        {!brief && <li className="text-sm text-muted-foreground md:col-span-5" data-testid="pipeline-loading">Loading case progress…</li>}
      </ol>
    </section>
  );
};
