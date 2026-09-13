import { Check } from "lucide-react";

export const CaseProgress = ({ stage, compact }) => {
  if (!stage) return null;
  const { index, steps, label } = stage;
  return (
    <div className={compact ? "mt-1.5" : "mt-3"} data-testid="case-progress" aria-label={`Stage: ${label}`}>
      <ol className="flex items-center gap-1">
        {steps.map((s, i) => (
          <li key={s} className="flex items-center gap-1 flex-1 min-w-0" title={s}>
            <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${i < index ? "bg-brand-purple text-white" : i === index ? "bg-align-yellow text-yellow-950 ring-2 ring-align-yellow/40" : "bg-border text-muted-foreground"}`} data-testid={`case-progress-step-${i}`}>
              {i < index ? <Check className="h-2.5 w-2.5" /> : i + 1}
            </span>
            {i < steps.length - 1 && <span className={`h-0.5 flex-1 rounded ${i < index ? "bg-brand-purple" : "bg-border"}`} />}
          </li>
        ))}
      </ol>
      {!compact && <p className="mt-1.5 text-xs font-medium text-brand-purple" data-testid="case-progress-label">{label}</p>}
    </div>
  );
};
