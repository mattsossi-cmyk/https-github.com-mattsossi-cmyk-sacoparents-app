import { Link } from "react-router-dom";
import { ShieldCheck, Lock } from "lucide-react";

const One = ({ role, name, scr, caseId }) => {
  if (!scr) return <p className="text-xs text-muted-foreground" data-testid={`lens-imported-screening-${role}-none`}>{name}: safety screening — Not Received.</p>;
  const date = typeof scr.completed_at === "string" && scr.completed_at ? scr.completed_at.slice(0, 10) : "";
  const ver = scr.version ? `Version ${scr.version}` : "legacy format";
  const tier = scr.tier ? { 1: "Tier 1 — resources only", 2: "Tier 2 — professional follow-up suggested", 3: "Tier 3 — professional follow-up recommended" }[scr.tier] : "Tier not available";
  return (
    <div className={`rounded-md border p-2 ${scr.tier === 3 ? "border-amber-300 bg-amber-50" : "border-teal-200 bg-[#e8f7f7]/60"}`} data-testid={`lens-imported-screening-${role}`}>
      <p className="text-xs font-semibold text-teal-900">{name}: safety screening — <span data-testid={`lens-imported-screening-${role}-status`}>Received</span> · {ver} · {scr.source || "sacoparentsalign.com"}{date ? ` · completed ${date}` : ""}</p>
      <p className="mt-1 text-xs" data-testid={`lens-imported-screening-${role}-tier`}>{tier}</p>
      {caseId && <Link to={`/joint/${caseId}/safety-screening/${role}`} className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-brand-purple hover:underline" data-testid={`lens-imported-screening-${role}-view`}><Lock className="h-3 w-3" /> View item-level responses (professional-only, access logged)</Link>}
    </div>
  );
};

export const ImportedScreening = ({ screening, rep, caseId }) => {
  if (!screening) return null;
  return (
    <div className="space-y-2 rounded-md border border-border bg-white p-3" data-testid="lens-imported-screening">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-teal-700"><ShieldCheck className="h-3.5 w-3.5" /> Private safety screenings (Version A / B / C)</p>
      <One role="a" name={rep.parent_a_name || "Parent A"} scr={screening.a} caseId={caseId} />
      <One role="b" name={rep.parent_b_name || "Parent B"} scr={screening.b} caseId={caseId} />
      <p className="text-[11px] italic text-muted-foreground" data-testid="lens-imported-screening-note">Screening questions adapted from published sources. Not a validated or diagnostic instrument. Tiers are a design guide, not a clinical cutoff. Answers are never printed in the report or PDF.</p>
    </div>
  );
};
