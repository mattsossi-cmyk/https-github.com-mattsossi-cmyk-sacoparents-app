import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const SERIES = [["statement", "Ability Level (statement)", "#5B2A86", "4 2"], ["joint", "Joint dynamic", "#0f766e", ""], ["parent_a", "Parent A", "#b45309", ""], ["parent_b", "Parent B", "#1d4ed8", ""]];

export function ScoreTrendChart({ history = [], names = {} }) {
  const rows = history.filter((h) => h.score || h.ratings).map((h) => ({ name: `v${h.version}`, date: h.at?.slice(0, 10), statement: h.score ?? null, joint: h.ratings?.joint ?? null, parent_a: h.ratings?.parent_a ?? null, parent_b: h.ratings?.parent_b ?? null }));
  if (rows.length < 2) return null;
  const label = (k) => (k === "parent_a" && names.a) || (k === "parent_b" && names.b) || SERIES.find((s) => s[0] === k)[1];
  return (
    <div className="rounded-lg border border-border bg-white p-4" data-testid="score-trend-chart">
      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Score trend across submitted versions (1–10)</p>
      <div className="h-56 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis domain={[1, 10]} ticks={[1, 3, 5, 7, 10]} tick={{ fontSize: 11 }} />
            <Tooltip labelFormatter={(l, p) => `${l} · ${p?.[0]?.payload?.date || ""}`} formatter={(v, k) => [v, label(k)]} />
            <Legend formatter={(k) => label(k)} wrapperStyle={{ fontSize: 11 }} />
            {SERIES.filter(([k]) => rows.some((r) => r[k] != null)).map(([k, , color, dash]) => <Line key={k} type="monotone" dataKey={k} name={k} stroke={color} strokeWidth={2} strokeDasharray={dash} dot={{ r: 4 }} connectNulls isAnimationActive={false} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11px] text-muted-foreground mt-1">Ratings describe the co-parenting context at each submission; they are not findings about either parent's fitness or credibility.</p>
    </div>
  );
}
