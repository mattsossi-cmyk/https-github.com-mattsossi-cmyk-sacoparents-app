const TH = ({ cols }) => <thead><tr className="bg-brand-purple/10 text-brand-purple">{cols.map((h) => <th key={h} className="border border-border p-2 text-left">{h}</th>)}</tr></thead>;
const rowCls = (hit, i) => hit ? "bg-amber-100 outline outline-2 outline-amber-500" : i % 2 ? "bg-secondary/40" : "";

export function IndividualScaleTable({ scale = [], row, rating, role, name, growth = [] }) {
  const label = name || `Parent ${role.toUpperCase()}`;
  return (
    <div className="space-y-1" data-testid={`lens-individual-scale-${role}`}>
      <p className="text-sm font-bold text-brand-teal">{label} — Individual Challenges & Growth{rating ? ` (Rated: Level ${rating})` : ""}</p>
      <div className="overflow-x-auto"><table className="w-full border-collapse text-xs">
        <TH cols={["Score", "Dynamic & Mode", "Where This Parent Does Well (Strengths)", "Where This Parent Does Poorly (Challenges)", "Placement & Growth Areas"]} />
        <tbody>{scale.map((r, i) => { const hit = row === i; const k = role === "a" ? "a" : "b"; return (
          <tr key={r.lo} className={rowCls(hit, i)} data-testid={`lens-individual-scale-${role}-row-${i}`}>
            <td className="border border-border p-2 font-bold whitespace-nowrap">{r.lo} – {r.hi}</td>
            <td className="border border-border p-2"><strong>{r.label}</strong><br /><em>({r.mode})</em></td>
            <td className="border border-border p-2">{r.well[k]}</td>
            <td className="border border-border p-2">{r.poor[k]}</td>
            <td className="border border-border p-2" data-testid={`lens-individual-scale-${role}-placement-${i}`}>{hit && <>
              <div className="font-bold">{label.toUpperCase()} (L{rating})</div>
              {growth.length > 0 && <ul className="mt-1 space-y-0.5">{growth.map((g, gi) => <li key={gi} className={g.met ? "text-align-green" : ""}>{g.met ? "✓" : "○"} {g.text}{g.met && <strong className="ml-1 text-[10px]">MET</strong>}</li>)}</ul>}
            </>}</td>
          </tr>); })}</tbody>
      </table></div>
    </div>
  );
}

export function JointScaleTable({ scale = [], row, rating }) {
  return (
    <div className="space-y-1" data-testid="lens-scale-table">
      <p className="text-sm font-bold text-brand-teal">Joint Co-Parenting Dynamic{rating ? ` (Rated: Level ${rating})` : ""}</p>
      <div className="overflow-x-auto"><table className="w-full border-collapse text-xs">
        <TH cols={["Score", "Dynamic & Mode", "Where Co-Parents Do Well (Strengths)", "Where Co-Parents Do Poorly (Gaps)", "Case Placement"]} />
        <tbody>{scale.map((r, i) => { const hit = row === i; return (
          <tr key={r.lo} className={rowCls(hit, i)} data-testid={`lens-scale-row-${i}`}>
            <td className="border border-border p-2 font-bold whitespace-nowrap">{r.lo} – {r.hi}</td>
            <td className="border border-border p-2"><strong>{r.label}</strong><br /><em>({r.mode})</em></td>
            <td className="border border-border p-2">{r.well.joint}</td>
            <td className="border border-border p-2">{r.poor.joint}</td>
            <td className="border border-border p-2 font-bold" data-testid={`lens-scale-placement-${i}`}>{hit && `JOINT (L${rating})`}</td>
          </tr>); })}</tbody>
      </table></div>
    </div>
  );
}

const growthOf = (rep, role) => (rep[`parent_${role}_growth`] || "").split("\n").map((s) => s.trim()).filter(Boolean).map((t) => ({ text: t, met: !!(rep.growth_status?.[role] || {})[t] }));

export function ScaleTable({ scale = [], cls = {}, rep = {} }) {
  return (
    <div className="space-y-5" data-testid="lens-scale-tables">
      <IndividualScaleTable scale={scale} row={cls.parent_a?.row} rating={rep.parent_a_rating} role="a" name={rep.parent_a_name} growth={growthOf(rep, "a")} />
      <IndividualScaleTable scale={scale} row={cls.parent_b?.row} rating={rep.parent_b_rating} role="b" name={rep.parent_b_name} growth={growthOf(rep, "b")} />
      <JointScaleTable scale={scale} row={cls.joint?.row} rating={rep.joint_rating} />
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
