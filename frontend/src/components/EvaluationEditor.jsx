import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

const H = ({ n, children }) => <h4 className="mt-5 border-b border-border pb-1 text-sm font-bold text-brand-purple">{n}. {children}</h4>;

export function EvaluationEditor({ fields, matrix, onChange, readOnly }) {
  const f = fields || {};
  const set = (k, v) => onChange?.({ ...f, [k]: v });
  const setProfile = (k, sub, v) => set(k, { ...(f[k] || {}), [sub]: v });
  const setScale = (sub, v) => set("scale", { ...(f.scale || {}), [sub]: v });
  const list = (k) => (Array.isArray(f[k]) ? f[k].join("\n") : "");
  const setList = (k, t) => set(k, t.split("\n").map((s) => s.trim()).filter(Boolean));
  const joint = Number(f.scale?.joint) || 0;
  const inBand = (range) => { const [lo, hi] = range.split("–").map((x) => Number(x.trim())); return joint >= lo && joint <= hi; };
  const T = (props) => readOnly ? <p className="mt-1 text-sm whitespace-pre-line" data-testid={props["data-testid"]}>{props.value || "—"}</p> : <Textarea {...props} className={`mt-1 min-h-[60px] ${props.className || ""}`} />;

  return (
    <div data-testid="evaluation-editor">
      <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Professional Evaluation — professional only, never shared with parents or attached to court automatically</p>
      <H n={1}>Safety First: Domestic Violence &amp; IPV Screening</H>
      <div className="mt-2 rounded-r-md border-l-4 border-amber-400 bg-amber-50 p-3 text-sm">
        <T value={f.safety_status || ""} onChange={(e) => set("safety_status", e.target.value)} data-testid="eval-safety-status" />
      </div>
      <H n={2}>Individual Profiles: Parent A &amp; Parent B</H>
      <div className="mt-2 grid gap-3 sm:grid-cols-2">
        {[["parent_a_profile", "Parent A"], ["parent_b_profile", "Parent B"]].map(([k, label]) => (
          <div key={k} className="rounded-lg border border-border bg-secondary/30 p-3" data-testid={`eval-${k}`}>
            <p className="text-sm font-semibold text-accent">{label}{f.scale?.[k === "parent_a_profile" ? "parent_a" : "parent_b"] ? ` (Score ${f.scale[k === "parent_a_profile" ? "parent_a" : "parent_b"]})` : ""}</p>
            <label className="mt-2 block text-xs font-semibold">Strengths (Doing Well)<T value={f[k]?.strengths || ""} onChange={(e) => setProfile(k, "strengths", e.target.value)} data-testid={`eval-${k}-strengths`} /></label>
            <label className="mt-2 block text-xs font-semibold">Gaps (Struggling)<T value={f[k]?.gaps || ""} onChange={(e) => setProfile(k, "gaps", e.target.value)} data-testid={`eval-${k}-gaps`} /></label>
          </div>
        ))}
      </div>
      <H n={3}>Comprehensive 1–10 Scale Analysis Matrix</H>
      {!readOnly && (
        <div className="mt-2 flex flex-wrap items-end gap-3 text-xs">
          {[["parent_a", "Parent A"], ["parent_b", "Parent B"], ["joint", "Joint"]].map(([k, l]) => (
            <label key={k} className="font-semibold">{l}<Input type="number" min={1} max={10} value={f.scale?.[k] ?? ""} onChange={(e) => setScale(k, Number(e.target.value))} className="mt-1 h-8 w-20" data-testid={`eval-scale-${k}`} /></label>
          ))}
        </div>
      )}
      <div className="mt-2 overflow-x-auto">
        <table className="w-full border-collapse text-xs" data-testid="eval-scale-matrix">
          <thead><tr className="bg-brand-purple/10 text-left text-brand-purple"><th className="border border-border p-2">Score</th><th className="border border-border p-2">Mode</th><th className="border border-border p-2">Strengths (Doing Well)</th><th className="border border-border p-2">Gaps (Struggling)</th><th className="border border-border p-2">Placement</th></tr></thead>
          <tbody>
            {(matrix || []).map((row) => {
              const hit = inBand(row.range);
              const placed = [f.scale?.parent_a && inBandFor(f.scale.parent_a, row.range) && "Parent A", f.scale?.parent_b && inBandFor(f.scale.parent_b, row.range) && "Parent B", hit && "Joint"].filter(Boolean);
              return (
                <tr key={row.range} className={hit ? "bg-amber-50 outline outline-2 outline-amber-400" : ""} data-testid={`eval-matrix-row-${row.range.replace(/\s/g, "")}`}>
                  <td className="border border-border p-2 font-bold">{row.range}</td><td className="border border-border p-2 font-medium">{row.mode}</td>
                  <td className="border border-border p-2">{row.strengths}</td><td className="border border-border p-2">{row.gaps}</td>
                  <td className="border border-border p-2 font-semibold text-amber-800">{placed.length ? placed.join(", ") : "--"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <label className="mt-2 block text-xs font-semibold">Rationale<T value={f.scale?.rationale || ""} onChange={(e) => setScale("rationale", e.target.value)} data-testid="eval-scale-rationale" /></label>
      <H n={4}>Actionable Growth Roadmap</H>
      <div className="mt-2 grid gap-3 sm:grid-cols-2">
        <label className="block text-xs font-semibold">Short-Term Goals (Next 30–90 Days) <span className="font-normal text-muted-foreground">one per line</span><T value={readOnly ? list("short_term_goals") : list("short_term_goals")} onChange={(e) => setList("short_term_goals", e.target.value)} data-testid="eval-short-term" /></label>
        <label className="block text-xs font-semibold">Long-Term Goals (6–12 Months) <span className="font-normal text-muted-foreground">one per line</span><T value={list("long_term_goals")} onChange={(e) => setList("long_term_goals", e.target.value)} data-testid="eval-long-term" /></label>
      </div>
      <H n={5}>Resource &amp; Referral Network</H>
      <table className="mt-2 w-full border-collapse text-xs" data-testid="eval-resources">
        <thead><tr className="bg-brand-purple/10 text-left text-brand-purple"><th className="border border-border p-2">Category</th><th className="border border-border p-2">Resource / Specialist</th><th className="border border-border p-2">Scope</th></tr></thead>
        <tbody>
          {(f.resources || []).length === 0 && <tr><td colSpan={3} className="border border-border p-2 italic text-muted-foreground">No resources drafted — the professional selects appropriate resources.</td></tr>}
          {(f.resources || []).map((r, i) => <tr key={i}><td className="border border-border p-2">{r.category}</td><td className="border border-border p-2 font-semibold">{r.resource}</td><td className="border border-border p-2">{r.scope}</td></tr>)}
        </tbody>
      </table>
    </div>
  );
}

function inBandFor(score, range) { const [lo, hi] = range.split("–").map((x) => Number(x.trim())); return score >= lo && score <= hi; }
