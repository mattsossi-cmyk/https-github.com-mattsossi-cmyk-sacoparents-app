export function FrameworkPanel({ st, setSt, suggestion, tiers }) {
  const score = st.dynamic_score || suggestion?.score || 5;
  const tier = (tiers || []).find((t) => score >= t.range[0] && score <= t.range[1]) || tiers?.[0];
  const choices = st.framework_choices || {};
  const on = (k, item) => !(choices[k] || tier?.[k] || []).length || (choices[k] || tier[k]).includes(item);
  const toggle = (k, item) => {
    const cur = choices[k] || tier[k];
    setSt({ ...st, dynamic_score: score, framework_choices: { ...choices, [k]: cur.includes(item) ? cur.filter((x) => x !== item) : [...cur, item] } });
  };
  if (!tier) return null;
  return (
    <div className="mt-5 rounded-lg border border-border p-4" data-testid="framework-panel">
      <p className="text-sm font-semibold">Co-Parenting Dynamic Scale (1–10)</p>
      <p className="text-xs text-muted-foreground">Options, resources and conflict-management techniques appear in this professional report only — never in the parents' Joint Report.{suggestion && <> Suggested from the Joint Report: <strong>{suggestion.score}</strong> ({suggestion.rationale})</>}</p>
      <div className="mt-3 flex items-center gap-3">
        <span className="text-xs">1 High conflict</span>
        <input type="range" min="1" max="10" value={score} onChange={(e) => setSt({ ...st, dynamic_score: Number(e.target.value), framework_choices: {} })} className="flex-1 accent-brand-purple" data-testid="framework-slider" />
        <span className="text-xs">10 Collaborative</span>
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white" style={{ background: tier.color }} data-testid="framework-score">{score}</span>
      </div>
      <p className="mt-2 inline-block rounded-full px-3 py-1 text-xs font-semibold text-white" style={{ background: tier.color }} data-testid="framework-tier">{tier.label}</p>
      {tier.safety_alert && <p className="mt-2 rounded-md border-l-4 border-red-600 bg-red-50 p-2 text-xs text-red-800" data-testid="framework-safety-alert"><strong>High-Conflict / Safety Protocols Active.</strong> All direct verbal interactions should be eliminated; child-welfare communication via structured digital mediums only.</p>}
      <p className="mt-3 text-sm"><strong>{tier.framework_title}.</strong> {tier.framework}</p>
      {[["techniques", "Communication & Conflict-Resolution Techniques"], ["tools", "Recommended Tools & Platforms"], ["resources", "Options & Resources"]].map(([k, label]) => (
        <div key={k} className="mt-3">
          <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label} <span className="font-normal normal-case">— untick anything that doesn't apply</span></p>
          <ul className="mt-1 space-y-1">{tier[k].map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={on(k, item)} onChange={() => toggle(k, item)} data-testid={`framework-item-${k}`} /><span>{item}</span></li>
          ))}</ul>
        </div>
      ))}
    </div>
  );
}
