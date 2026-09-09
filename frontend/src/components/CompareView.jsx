import { useMemo, useState } from "react";
import { CheckCircle2, AlertCircle, MinusCircle, Columns2, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

const STATUS = {
  "Strong alignment": { key: "agree", icon: CheckCircle2, cls: "text-align-green", chip: "bg-align-green/15 text-align-green" },
  "Moderate alignment": { key: "partial", icon: MinusCircle, cls: "text-yellow-700", chip: "bg-align-yellow/25 text-yellow-800" },
  "Needs discussion": { key: "differ", icon: AlertCircle, cls: "text-align-purple", chip: "bg-align-purple/10 text-align-purple" },
};

export function CompareView({ report, onOpenReport }) {
  const [filter, setFilter] = useState("all");
  const diffByArea = useMemo(() => Object.fromEntries((report.differences || []).map((d) => [d.area, d])), [report]);
  const rows = (report.alignment_map || []).map((r) => ({ ...r, meta: STATUS[r.status] || STATUS["Needs discussion"], diff: diffByArea[r.area] }));
  const counts = rows.reduce((c, r) => ({ ...c, [r.meta.key]: (c[r.meta.key] || 0) + 1 }), {});
  const shown = rows.filter((r) => filter === "all" || r.meta.key === filter);

  return (
    <div className="bg-white border border-border rounded-lg p-6 sm:p-8 mb-8" data-testid="compare-view">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-brand-teal"><Columns2 className="h-5 w-5" /><p className="text-xs uppercase tracking-widest font-bold">Compare · professional view</p></div>
          <h2 className="text-2xl font-semibold mt-1">Where {report.parent_a_name} and {report.parent_b_name} agree — and where they differ</h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">Side-by-side look at both parents' individual reflections about {report.child_name}. Use it to plan the conversation before you generate the Joint Alignment Report. Neither parent sees this view.</p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={onOpenReport} data-testid="compare-open-report-btn"><FileText className="h-4 w-4" /> View full report</Button>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-6" data-testid="compare-summary">
        {[["agree", "Agree", counts.agree], ["partial", "Partly aligned", counts.partial], ["differ", "Differ", counts.differ]].map(([k, label, n]) => (
          <button key={k} type="button" onClick={() => setFilter(filter === k ? "all" : k)} className={`rounded-lg border p-4 text-left transition-colors ${filter === k ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`} data-testid={`compare-count-${k}`} aria-pressed={filter === k}>
            <p className="text-3xl font-semibold">{n || 0}</p>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mt-1">{label}</p>
          </button>
        ))}
      </div>

      {report.alignment_statements?.length > 0 && filter !== "differ" && (
        <div className="mt-6 bg-align-green/10 border border-align-green/30 rounded-lg p-4" data-testid="compare-agree-list">
          <p className="text-sm font-semibold text-align-green mb-2">Both parents identified</p>
          <ul className="space-y-1.5">{report.alignment_statements.map((s, i) => <li key={i} className="flex items-start gap-2 text-sm"><CheckCircle2 className="h-4 w-4 text-align-green shrink-0 mt-0.5" />{s}</li>)}</ul>
        </div>
      )}

      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm" data-testid="compare-table">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
              <th className="py-2 pr-3 w-44">Area</th>
              <th className="py-2 pr-3">{report.parent_a_name}</th>
              <th className="py-2 pr-3">{report.parent_b_name}</th>
              <th className="py-2 w-40">Alignment</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const Icon = r.meta.icon;
              return (
                <tr key={r.area} className="border-b border-border align-top" data-testid={`compare-row-${r.meta.key}`}>
                  <td className="py-3 pr-3 font-medium">{r.area}</td>
                  <td className="py-3 pr-3 text-muted-foreground">{r.diff ? r.diff.parent_a || <em>No response</em> : <span className="text-align-green">Shared perspective</span>}</td>
                  <td className="py-3 pr-3 text-muted-foreground">{r.diff ? r.diff.parent_b || <em>No response</em> : <span className="text-align-green">Shared perspective</span>}</td>
                  <td className="py-3"><span className={`inline-flex items-center gap-1.5 text-xs font-semibold rounded-full px-2.5 py-1 ${r.meta.chip}`}><Icon className="h-3.5 w-3.5" />{r.status}</span></td>
                </tr>
              );
            })}
            {shown.length === 0 && <tr><td colSpan={4} className="py-6 text-center text-muted-foreground" data-testid="compare-empty">Nothing in this category.</td></tr>}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-xs text-muted-foreground italic">Differences are shown as perspectives, not positions. The parents expressed different perspectives regarding these areas; additional discussion may be helpful, centred on {report.child_name}'s needs.</p>
    </div>
  );
}
