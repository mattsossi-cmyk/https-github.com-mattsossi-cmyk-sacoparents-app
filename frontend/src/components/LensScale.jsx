const WP = ({ r, k }) => <><strong>Joint:</strong> {r[k].joint}<br /><strong>Parent A:</strong> {r[k].a}<br /><strong>Parent B:</strong> {r[k].b}</>;

export function ScaleTable({ scale = [], cls = {}, rep = {} }) {
  const place = (i) => [cls.parent_a?.row === i && `PARENT A (L${rep.parent_a_rating})`, cls.parent_b?.row === i && `PARENT B (L${rep.parent_b_rating})`, cls.joint?.row === i && `JOINT (L${rep.joint_rating})`].filter(Boolean);
  return (
    <div className="overflow-x-auto" data-testid="lens-scale-table">
      <table className="w-full border-collapse text-xs">
        <thead><tr className="bg-brand-purple/10 text-brand-purple">{["Score", "Dynamic & Mode", "Where Co-Parents Do Well (Strengths)", "Where Co-Parents Do Poorly (Gaps)", "Case Placement"].map((h) => <th key={h} className="border border-border p-2 text-left">{h}</th>)}</tr></thead>
        <tbody>{scale.map((r, i) => { const p = place(i); return (
          <tr key={r.lo} className={p.length ? "bg-amber-100 outline outline-2 outline-amber-500" : i % 2 ? "bg-secondary/40" : ""} data-testid={`lens-scale-row-${i}`}>
            <td className="border border-border p-2 font-bold whitespace-nowrap">{r.lo} – {r.hi}</td>
            <td className="border border-border p-2"><strong>{r.label}</strong><br /><em>({r.mode})</em></td>
            <td className="border border-border p-2"><WP r={r} k="well" /></td>
            <td className="border border-border p-2"><WP r={r} k="poor" /></td>
            <td className="border border-border p-2 font-bold" data-testid={`lens-scale-placement-${i}`}>{p.map((x) => <div key={x}>{x}</div>)}</td>
          </tr>); })}</tbody>
      </table>
    </div>
  );
}

export function PathwayList({ pathways = [], rating, recommended, chosen, onChoose }) {
  const active = chosen || recommended;
  return (
    <ol className="space-y-2" data-testid="lens-pathways">
      {pathways.map((p, i) => (
        <li key={p.key} className={`rounded-md border p-3 text-sm ${active === p.key ? "border-amber-500 bg-amber-50" : "border-border bg-white"}`} data-testid={`lens-pathway-${p.key}`}>
          <div className="flex flex-wrap items-center gap-2">
            <strong>{i + 1}. {p.name} ({p.levels})</strong>
            {recommended === p.key && rating && <span className="rounded-full bg-amber-200 px-2 py-0.5 text-[10px] font-bold" data-testid="lens-pathway-recommended">Level {rating} Recommendation</span>}
            {onChoose && <label className="ml-auto flex items-center gap-1 text-xs"><input type="radio" checked={active === p.key} onChange={() => onChoose(p.key)} data-testid={`lens-pathway-pick-${p.key}`} /> Select</label>}
          </div>
          <p className="text-muted-foreground mt-1">{p.desc}</p>
        </li>
      ))}
    </ol>
  );
}
