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

const Pathway = ({ pw }) => pw ? (
  <div className="rounded-md border border-teal-200 bg-[#e8f7f7]/60 p-3 space-y-1.5" data-testid="lens-safety-pathway">
    <p className="text-xs font-bold uppercase tracking-widest text-teal-800">Safety pathway — professional's confirmed process consideration</p>
    <p className="text-sm font-semibold" data-testid="lens-safety-pathway-label">{pw.label}</p>
    <p className="text-xs"><span className="font-semibold">Child-focused needs (categories only):</span> {pw.child_needs.join(", ")}</p>
    <p className="text-xs font-semibold">Communication safeguards</p><ul className="list-disc pl-5 text-xs">{pw.safeguards.map((x) => <li key={x}>{x}</li>)}</ul>
    <p className="text-xs font-semibold">Decision-making options</p><ul className="list-disc pl-5 text-xs">{pw.decisions.map((x) => <li key={x}>{x}</li>)}</ul>
    {pw.court_order_notice && <p className="rounded border-l-4 border-amber-500 bg-amber-50 p-2 text-xs font-medium" data-testid="lens-safety-pathway-court-notice">{pw.court_order_notice}</p>}
    <p className="text-[11px] italic text-muted-foreground" data-testid="lens-safety-pathway-restricted">{pw.restricted_notice}</p>
    <p className="text-[11px] italic text-muted-foreground">{pw.note}</p>
  </div>
) : null;

export const ImportedScreening = ({ screening, rep, caseId, pathway }) => {
  if (!screening) return null;
  return (
    <div className="space-y-2 rounded-md border border-border bg-white p-3" data-testid="lens-imported-screening">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-teal-700"><ShieldCheck className="h-3.5 w-3.5" /> Private safety screenings (Version A / B / C)</p>
      <One role="a" name={rep.parent_a_name || "Parent A"} scr={screening.a} caseId={caseId} />
      <One role="b" name={rep.parent_b_name || "Parent B"} scr={screening.b} caseId={caseId} />
      <Pathway pw={pathway} />
      <p className="text-[11px] italic text-muted-foreground" data-testid="lens-imported-screening-note">Screening questions adapted from published sources. Not a validated or diagnostic instrument. Tiers are a design guide, not a clinical cutoff. Answers are never printed in the report or PDF.</p>
    </div>
  );
};
