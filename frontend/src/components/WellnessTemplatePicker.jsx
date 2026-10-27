import { Sparkles } from "lucide-react";
import { WELLNESS_TEMPLATES } from "@/data/wellnessTemplates";

export const WellnessTemplatePicker = ({ onPick, testIdPrefix = "wellness-template" }) => (
  <div className="mt-3 rounded-md border border-dashed border-brand-purple/40 bg-[#faf8fd] p-3" data-testid={`${testIdPrefix}-picker`}>
    <p className="flex items-center gap-1.5 text-xs font-semibold text-brand-purple"><Sparkles className="h-3.5 w-3.5" /> Start from a template — pick one, then edit it in your own words</p>
    <div className="mt-2 grid gap-2 sm:grid-cols-3">
      {WELLNESS_TEMPLATES.map((t) => (
        <button key={t.id} type="button" onClick={() => onPick(t)} className="rounded-md border border-border bg-white px-3 py-2 text-left transition-colors hover:border-brand-purple hover:bg-brand-purple/5" data-testid={`${testIdPrefix}-${t.id}`}>
          <span className="block text-sm font-semibold">{t.title}</span>
          <span className="block text-xs text-muted-foreground">{t.blurb}</span>
        </button>
      ))}
    </div>
  </div>
);
