import { Baby, PenLine, Columns2, Target, Lightbulb, Handshake, ArrowRight } from "lucide-react";

const STAGES = [
  { key: "reflection", label: "Reflection", icon: PenLine, body: "Each parent reflects privately." },
  { key: "comparison", label: "Comparison", icon: Columns2, body: "Align lines up both perspectives." },
  { key: "alignment", label: "Alignment", icon: Target, body: "Shared ground and differences, without blame." },
  { key: "options", label: "Options", icon: Lightbulb, body: "Neutral options and resources." },
  { key: "agreement", label: "Agreement", icon: Handshake, body: "Alignment becomes the foundation." },
];

export const AlignModel = () => (
  <div data-testid="align-model">
    <div className="relative mx-auto max-w-3xl">
      <div className="flex justify-center mb-8">
        <div className="relative h-36 w-36 rounded-full bg-brand-purple text-white flex flex-col items-center justify-center shadow-xl ring-8 ring-brand-purple/15" data-testid="align-model-child">
          <Baby className="h-9 w-9" />
          <span className="mt-1 text-sm font-extrabold uppercase tracking-widest">The Child</span>
          <span className="text-[10px] text-white/80">at the center</span>
        </div>
      </div>
      <ol className="grid grid-cols-1 sm:grid-cols-5 gap-3 sm:gap-2 items-stretch" data-testid="align-model-stages">
        {STAGES.map((s, i) => (
          <li key={s.key} className="relative flex sm:flex-col items-center sm:items-stretch gap-3 sm:gap-0" data-testid={`align-model-stage-${s.key}`}>
            <div className="flex-1 bg-white border border-border rounded-xl p-4 text-left sm:text-center hover:-translate-y-0.5 hover:shadow-md transition-[transform,box-shadow] duration-200 h-full">
              <s.icon className="h-6 w-6 text-brand-teal sm:mx-auto" />
              <p className="mt-2 font-bold text-sm uppercase tracking-wide text-brand-purple">{s.label}</p>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{s.body}</p>
            </div>
            {i < STAGES.length - 1 && (
              <ArrowRight className="hidden sm:block absolute -right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-brand-purple/60 z-10" />
            )}
          </li>
        ))}
      </ol>
    </div>
  </div>
);
