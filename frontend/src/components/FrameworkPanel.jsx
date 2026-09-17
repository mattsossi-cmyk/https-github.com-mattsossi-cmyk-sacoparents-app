import { useState } from "react";
import { Plus, X } from "lucide-react";
import { ResourceLibrary } from "@/components/ResourceLibrary";

const GROUPS = [["subject_options", "Options for the assessed subject", "Infused from the Joint Report — shown only when the parents differ on this subject"],
  ["resources", "Options & Resources", "Classes, counseling, mediation, facilitators"], ["tools", "Tools & Platforms", ""], ["techniques", "Conflict-Management Techniques", ""]];

function AddOwn({ onAdd, k }) {
  const [v, setV] = useState("");
  const add = () => { if (v.trim()) { onAdd(v.trim()); setV(""); } };
  return (
    <div className="mt-1.5 flex gap-2">
      <input value={v} onChange={(e) => setV(e.target.value)} onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())} placeholder="Add your own…" className="h-8 flex-1 rounded-md border border-input bg-white px-2 text-xs" data-testid={`framework-custom-input-${k}`} />
      <button type="button" onClick={add} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2 text-xs hover:bg-secondary" data-testid={`framework-custom-add-${k}`}><Plus className="h-3 w-3" /> Add</button>
    </div>
  );
}

export function FrameworkPanel({ st, setSt, suggestion, tiers, subjectOptions = [], library = {}, orgLibrary = {}, organization = "", onLibraryChange, onOrgLibraryChange, lastSubmittedScore }) {
  const score = st.dynamic_score || suggestion?.score || 5;
  const tier = (tiers || []).find((t) => score >= t.range[0] && score <= t.range[1]) || tiers?.[0];
  const choices = st.framework_choices || {};
  const custom = st.framework_custom || {};
  const saved = (k) => [...(library[k] || []), ...(orgLibrary[k] || [])];
  const lib = (k) => (k === "subject_options" ? subjectOptions : [...(tier?.[k] || []), ...saved(k).filter((i, idx, arr) => !(tier?.[k] || []).includes(i) && arr.indexOf(i) === idx)]);
  const badge = (k, item) => ((tier?.[k] || []).includes(item) ? null : (library[k] || []).includes(item) ? "MY LIBRARY" : (orgLibrary[k] || []).includes(item) ? "ORG" : null);
  const levelChanged = lastSubmittedScore && lastSubmittedScore !== score;
  const on = (k, item) => !(k in choices) || choices[k].includes(item);
  const toggle = (k, item) => {
    const cur = k in choices ? choices[k] : lib(k);
    setSt({ ...st, dynamic_score: score, framework_choices: { ...choices, [k]: cur.includes(item) ? cur.filter((x) => x !== item) : [...cur, item] } });
  };
  const addCustom = (k, text) => setSt({ ...st, dynamic_score: score, framework_custom: { ...custom, [k]: [...(custom[k] || []), text] } });
  const removeCustom = (k, i) => setSt({ ...st, framework_custom: { ...custom, [k]: custom[k].filter((_, j) => j !== i) } });
  if (!tier) return null;
  return (
    <div className="mt-5 rounded-lg border border-border p-4" data-testid="framework-panel">
      <p className="text-sm font-semibold">Co-Parenting Ability Level (1–10)</p>
      <p className="text-xs text-muted-foreground">Options, resources and conflict-management techniques appear in the Professional Report only — visible to you and the court, never to the parents.</p>
      {suggestion && <p className="mt-1 text-xs rounded-md bg-secondary/60 px-2 py-1.5" data-testid="framework-suggestion">Suggested from the Joint Report: <strong>Level {suggestion.score}</strong> — {suggestion.rationale}</p>}
      <div className="mt-3 flex items-center gap-3">
        <span className="text-xs">1 High conflict</span>
        <input type="range" min="1" max="10" value={score} onChange={(e) => setSt({ ...st, dynamic_score: Number(e.target.value), framework_choices: {} })} className="flex-1 accent-brand-purple" data-testid="framework-slider" />
        <span className="text-xs">10 Collaborative</span>
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white" style={{ background: tier.color }} data-testid="framework-score">{score}</span>
      </div>
      <p className="mt-2 inline-block rounded-full px-3 py-1 text-xs font-semibold text-white" style={{ background: tier.color }} data-testid="framework-tier">{tier.label}</p>
      {tier.safety_alert && <p className="mt-2 rounded-md border-l-4 border-red-600 bg-red-50 p-2 text-xs text-red-800" data-testid="framework-safety-alert"><strong>High-Conflict / Safety Protocols Active.</strong> All direct verbal interactions should be eliminated; child-welfare communication via structured digital mediums only.</p>}
      {levelChanged && (
        <label className="mt-3 block rounded-md border border-amber-300 bg-amber-50 p-3 text-xs" data-testid="level-change-note-box">
          <span className="font-semibold text-amber-900">Level changed from {lastSubmittedScore} to {score} since the last court submission.</span>
          <span className="block text-amber-800">Add a neutral one-line reason for the court (required before marking ready). No findings about either parent.</span>
          <input value={st.level_change_note || ""} onChange={(e) => setSt({ ...st, level_change_note: e.target.value })} maxLength={300} placeholder="e.g., Parents completed two facilitated sessions and now use written-only scheduling." className="mt-2 h-9 w-full rounded-md border border-input bg-white px-2 text-sm" data-testid="level-change-note" />
        </label>
      )}
      <p className="mt-3 text-sm"><strong>{tier.framework_title}.</strong> {tier.framework}</p>
      {GROUPS.map(([k, label, hint]) => (k !== "subject_options" || subjectOptions.length > 0) && (
        <div key={k} className="mt-3" data-testid={`framework-group-${k}`}>
          <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label} <span className="font-normal normal-case">— untick anything that doesn't apply{hint ? `. ${hint}` : ""}</span></p>
          <ul className="mt-1 space-y-1">
            {lib(k).map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={on(k, item)} onChange={() => toggle(k, item)} data-testid={`framework-item-${k}`} />{badge(k, item) && <span className="mt-0.5 rounded bg-align-green/15 px-1 text-[10px] font-bold text-align-green" data-testid={`framework-library-badge-${k}`}>{badge(k, item)}</span>}<span>{item}</span></li>
            ))}
            {(custom[k] || []).map((item, i) => (
              <li key={`c${i}`} className="flex items-start gap-2 text-sm" data-testid={`framework-custom-item-${k}`}><span className="mt-0.5 rounded bg-brand-purple/10 px-1 text-[10px] font-bold text-brand-purple">OWN</span><span className="flex-1">{item}</span><button type="button" onClick={() => removeCustom(k, i)} aria-label="Remove" data-testid={`framework-custom-remove-${k}`}><X className="h-3.5 w-3.5 text-muted-foreground" /></button></li>
            ))}
          </ul>
          {k !== "subject_options" && <AddOwn k={k} onAdd={(t) => addCustom(k, t)} />}
        </div>
      ))}
      {onLibraryChange && <ResourceLibrary library={library} orgLibrary={orgLibrary} organization={organization} onChange={onLibraryChange} onOrgChange={onOrgLibraryChange} />}
    </div>
  );
}
