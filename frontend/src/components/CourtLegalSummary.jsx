import { CheckCircle2, Circle, ShieldAlert } from "lucide-react";
import { IndividualScaleTable, JointScaleTable } from "@/components/LensScale";

const Block = ({ title, children, testId }) => <div className="rounded-lg border border-border p-4" data-testid={testId}><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{title}</p><div className="mt-2 text-sm space-y-2">{children}</div></div>;
const RISK_STYLE = { "High Risk": "bg-red-100 text-red-800", "Moderate-to-High Risk": "bg-orange-100 text-orange-800", "Moderate Risk": "bg-amber-100 text-amber-800", "Low Risk": "bg-align-green/15 text-align-green", "Not assessed": "bg-secondary text-muted-foreground" };
const Score = ({ s }) => s?.score ? <span className="inline-flex items-center gap-2"><span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-purple text-sm font-bold text-white">{s.score}</span><span>{s.label}{s.mode ? ` · ${s.mode} Mode` : ""}</span></span> : <span className="text-muted-foreground">—</span>;

export function GrowthList({ items = [], testId }) {
  return <ul className="space-y-1" data-testid={testId}>{items.map((g, i) => <li key={i} className="flex items-start gap-2">{g.met ? <CheckCircle2 className="h-4 w-4 shrink-0 text-align-green" /> : <Circle className="h-4 w-4 shrink-0 text-muted-foreground" />}<span className={g.met ? "" : "text-muted-foreground"}>{g.text}{g.met && <span className="ml-1 text-[10px] font-semibold text-align-green">MET</span>}</span></li>)}</ul>;
}

export function GrowthProgress({ met = 0, total = 0, testId }) {
  const pct = total ? Math.round((met / total) * 100) : 0;
  return (
    <div className="mt-1 mb-2" data-testid={testId} role="progressbar" aria-valuenow={met} aria-valuemin={0} aria-valuemax={total}>
      <div className="h-2 w-full overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full bg-align-green transition-[width] duration-500" style={{ width: `${pct}%` }} /></div>
      <p className="mt-1 text-[11px] text-muted-foreground">{total ? `${met} of ${total} growth areas met (${pct}%)` : "No growth areas recorded"}</p>
    </div>
  );
}

export function CourtLegalSummary({ s }) {
  if (!s) return null;
  const names = s.parent_names || {};
  return (
    <div className="space-y-3" data-testid="court-legal-summary">
      <Block title="Co-Parenting Ratings (1–10)" testId="court-legal-ratings">
        <div className="grid gap-2 sm:grid-cols-3">
          <div><p className="text-xs text-muted-foreground">{names.a || "Parent A"}</p><Score s={s.ratings?.parent_a} /></div>
          <div><p className="text-xs text-muted-foreground">{names.b || "Parent B"}</p><Score s={s.ratings?.parent_b} /></div>
          <div><p className="text-xs text-muted-foreground">Joint dynamic</p><Score s={s.ratings?.joint} /></div>
        </div>
      </Block>
      {s.scale_table && <Block title="1–10 Scale Placement — Individual, then Joint" testId="court-legal-scale">
        <div className="space-y-5">
          <IndividualScaleTable scale={s.scale_table} row={s.placement?.a} rating={s.ratings?.parent_a?.score} role="a" name={names.a} growth={s.growth?.a} />
          <IndividualScaleTable scale={s.scale_table} row={s.placement?.b} rating={s.ratings?.parent_b?.score} role="b" name={names.b} growth={s.growth?.b} />
          <JointScaleTable scale={s.scale_table} row={s.placement?.joint} rating={s.ratings?.joint?.score} />
        </div>
        <p className="text-[11px] italic text-muted-foreground">Reference scale recorded by the professional at finalization; placements are professional ratings, not court findings.</p>
      </Block>}
      <Block title="Safety First — IPV Risk Screening Summary" testId="court-legal-risk">
        <p className="text-xs text-muted-foreground">Family Violence assessments: Parent A {s.fv_received?.a || "—"} · Parent B {s.fv_received?.b || "—"} · Joint process appropriate: <strong>{s.joint_process_appropriate || "—"}</strong></p>
        <ul className="grid gap-1 sm:grid-cols-2">{(s.risk_screening || []).map((r) => <li key={r.label} className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${RISK_STYLE[r.level] || RISK_STYLE["Not assessed"]}`}>{r.level}</span><span className="font-medium">{r.label}</span>{r.note && <span className="text-xs text-muted-foreground">— {r.note}</span>}</li>)}</ul>
        {s.safety_takeaway && <p className="flex gap-2 rounded-md bg-amber-50 p-2 text-xs"><ShieldAlert className="h-4 w-4 shrink-0 text-amber-700" /><span><strong>Takeaway:</strong> {s.safety_takeaway}</span></p>}
        <p className="text-[11px] italic text-muted-foreground">Screening summary recorded by the professional; not a finding that any allegation is true.</p>
      </Block>
      <Block title="Key Growth Areas — progress at reassessment" testId="court-legal-growth">
        <div className="grid gap-3 sm:grid-cols-2">
          {["a", "b"].map((r) => { const items = s.growth?.[r] || []; const met = items.filter((g) => g.met).length; return <div key={r}><p className="font-semibold">{names[r] || `Parent ${r.toUpperCase()}`} <span className="text-xs text-muted-foreground">({met} of {items.length} met)</span></p><GrowthProgress met={met} total={items.length} testId={`court-legal-growth-progress-${r}`} /><GrowthList items={items} testId={`court-legal-growth-${r}`} /></div>; })}
        </div>
      </Block>
      <Block title="Conflict Resolution Pathway" testId="court-legal-pathway">
        <p><strong>{s.pathway || "Not selected"}</strong></p>{s.pathway_rationale && <p className="whitespace-pre-wrap text-muted-foreground">{s.pathway_rationale}</p>}
      </Block>
      <div className="grid gap-3 sm:grid-cols-2">
        <Block title="Short-Term Goals (30–90 days)" testId="court-legal-short"><ul className="list-disc pl-4 space-y-1">{(s.short_term_goals || []).map((g, i) => <li key={i}>{g}</li>)}</ul></Block>
        <Block title="Long-Term Goals (6–12 months)" testId="court-legal-long"><ul className="list-disc pl-4 space-y-1">{(s.long_term_goals || []).map((g, i) => <li key={i}>{g}</li>)}</ul></Block>
      </div>
      {s.resources?.length > 0 && <Block title="Resource & Support Options" testId="court-legal-resources"><ul className="space-y-1">{s.resources.map((r, i) => <li key={i}><span className="text-xs font-semibold text-brand-purple">{r.category}</span> · <strong>{r.resource}</strong>{r.focus && <span className="text-muted-foreground"> — {r.focus}</span>}</li>)}</ul></Block>}
      <p className="text-xs text-muted-foreground">Reassessment {s.reassess_interval ? s.reassess_interval.toLowerCase() : "—"}{s.next_review_date ? ` · next review ${s.next_review_date}` : ""}{s.finalized_at ? ` · report finalized ${s.finalized_at.slice(0, 10)}` : ""}</p>
    </div>
  );
}
