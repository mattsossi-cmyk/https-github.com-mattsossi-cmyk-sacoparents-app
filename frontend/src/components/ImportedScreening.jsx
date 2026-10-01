import { ShieldCheck } from "lucide-react";

const One = ({ role, name, scr }) => {
  if (!scr) return <p className="text-xs text-muted-foreground" data-testid={`lens-imported-screening-${role}-none`}>{name}: no imported safety screening on file.</p>;
  return (
    <details className="rounded-md border border-teal-200 bg-[#e8f7f7]/60 p-2" data-testid={`lens-imported-screening-${role}`}>
      <summary className="cursor-pointer text-xs font-semibold text-teal-900">
        {name}: safety screening received from {scr.source}{scr.completed_at ? ` · ${scr.completed_at.slice(0, 10)}` : ""} — {scr.item_count} items, <span data-testid={`lens-imported-screening-${role}-concerns`}>{scr.concern_count} indicated a concern</span>
      </summary>
      <p className="mt-2 text-[11px] italic text-muted-foreground">Parent-reported screening responses, shown to you for professional follow-up only. They are not findings and are never printed in the court PDF — only the receipt and counts above appear there.</p>
      <ul className="mt-2 space-y-1 text-xs">
        {scr.items.map((it, i) => <li key={i} className={`rounded px-2 py-1 ${it.concern ? "bg-amber-50 border border-amber-200" : "bg-white/70"}`} data-testid={`lens-imported-screening-${role}-item-${i}`}><span className="font-medium">{it.question}</span> — {it.answer}</li>)}
      </ul>
    </details>
  );
};

export const ImportedScreening = ({ screening, rep }) => {
  if (!screening) return null;
  return (
    <div className="space-y-2 rounded-md border border-border bg-white p-3" data-testid="lens-imported-screening">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-teal-700"><ShieldCheck className="h-3.5 w-3.5" /> Imported safety screening (sacoparentsapp.online)</p>
      <One role="a" name={rep.parent_a_name || "Parent A"} scr={screening.a} />
      <One role="b" name={rep.parent_b_name || "Parent B"} scr={screening.b} />
    </div>
  );
};
