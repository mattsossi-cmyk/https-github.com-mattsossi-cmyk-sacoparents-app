import { ArrowDown, ArrowUp, Minus } from "lucide-react";

const Delta = ({ prev, cur, testId }) => {
  if (prev == null || cur == null) return <span className="text-muted-foreground" data-testid={testId}>—</span>;
  const d = cur - prev;
  const Icon = d > 0 ? ArrowUp : d < 0 ? ArrowDown : Minus;
  const cls = d > 0 ? "text-align-green" : d < 0 ? "text-red-600" : "text-muted-foreground";
  return <span className={`inline-flex items-center gap-0.5 text-xs font-bold ${cls}`} data-testid={testId}><Icon className="h-3 w-3" />{d > 0 ? `+${d}` : d}</span>;
};

const growthPct = (g, k) => (g && g[k]?.total ? Math.round((g[k].met / g[k].total) * 100) : null);

export function ReassessmentCompare({ history = [], names = {} }) {
  const rows = history.filter((h) => h.score);
  if (rows.length < 2) return null;
  const prev = rows[rows.length - 2], cur = rows[rows.length - 1];
  const metrics = [
    ["Ability level (1–10)", (h) => h.score, "level"],
    [`${names.a || "Parent A"} rating`, (h) => h.ratings?.a, "a"],
    [`${names.b || "Parent B"} rating`, (h) => h.ratings?.b, "b"],
    ["Joint rating", (h) => h.ratings?.joint, "joint"],
    [`${names.a || "Parent A"} growth areas met`, (h) => growthPct(h.growth, "a"), "growth-a", (h) => h.growth?.a ? `${h.growth.a.met}/${h.growth.a.total}` : null],
    [`${names.b || "Parent B"} growth areas met`, (h) => growthPct(h.growth, "b"), "growth-b", (h) => h.growth?.b ? `${h.growth.b.met}/${h.growth.b.total}` : null],
  ];
  const show = (h, get, fmt) => { const v = get(h); if (v == null) return "—"; return fmt ? `${fmt(h)} (${v}%)` : v; };
  return (
    <div className="rounded-lg border border-brand-purple/30 bg-white p-4" data-testid="reassessment-compare">
      <p className="text-xs font-bold uppercase tracking-widest text-brand-purple">Reassessment comparison — previous vs. current submission</p>
      <div className="mt-2 overflow-x-auto"><table className="w-full border-collapse text-sm">
        <thead><tr className="text-left text-xs text-muted-foreground"><th className="py-1 pr-2"></th><th className="py-1 pr-2" data-testid="compare-prev-head">v{prev.version} · {prev.at?.slice(0, 10)}</th><th className="py-1 pr-2" data-testid="compare-cur-head">v{cur.version} · {cur.at?.slice(0, 10)}</th><th className="py-1">Change</th></tr></thead>
        <tbody>{metrics.map(([label, get, key, fmt]) => (
          <tr key={key} className="border-t border-border" data-testid={`compare-row-${key}`}>
            <td className="py-1.5 pr-2 font-medium">{label}</td><td className="py-1.5 pr-2">{show(prev, get, fmt)}</td><td className="py-1.5 pr-2 font-semibold">{show(cur, get, fmt)}</td>
            <td className="py-1.5"><Delta prev={get(prev)} cur={get(cur)} testId={`compare-delta-${key}`} /></td>
          </tr>))}</tbody>
      </table></div>
      {cur.note && <p className="mt-2 text-[11px] italic text-muted-foreground" data-testid="compare-note">Professional's note on the change: {cur.note}</p>}
      <p className="mt-1 text-[11px] text-muted-foreground">Ratings and growth status are the professional's assessments frozen with each submission — not court findings.</p>
    </div>
  );
}
